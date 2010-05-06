package edu.ucla.cens.stresschillmap;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Map;

import net.oauth.OAuth;
import net.oauth.OAuthAccessor;
import net.oauth.OAuthConsumer;
import net.oauth.OAuthException;
import net.oauth.OAuthMessage;
import net.oauth.OAuthServiceProvider;
import net.oauth.client.OAuthClient;
import net.oauth.client.httpclient4.HttpClient4;
import net.oauth.http.HttpMessage;

import org.apache.http.HttpResponse;
import org.apache.http.HttpStatus;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.mime.MultipartEntity;
import org.apache.http.entity.mime.content.FileBody;
import org.apache.http.entity.mime.content.StringBody;
import org.apache.http.impl.client.DefaultHttpClient;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.util.Log;
import android.widget.Toast;
import edu.ucla.cens.stresschillmap.survey_db.survey_db_row;

public class survey_upload extends Service{
    private survey_db sdb;

	PostThread post;

	public boolean ran = false;
	private static final String TAG = "SurveyUploadThread";

    private static HttpClient httpClient = new DefaultHttpClient();

    @Override
    public void onCreate() {
        /* XXX temporarily allow unauthorized upload... (testing and stuff)
        if (!preferences.getBoolean("authenticated", false)) {
            Log.d(TAG, "user is not authenticated... stopping this service");
            return;
        }
        */

		sdb = new survey_db(this);

		//if there are no entries to submit, we should just stop
		if(!sdb.has_entries()) {
			Log.d(TAG, "stopping?");
			stopSelf();
		} else {

			Toast.makeText(this, R.string.surveyuploadstarted, Toast.LENGTH_SHORT).show();

			post = new PostThread();
			post.start();
		}
    }

	@Override
	public IBinder onBind(Intent arg0) {
		// TODO Auto-generated method stub
		return null;
	}
	
    @Override
    public void onDestroy() {
        Log.d(TAG, "Stopping the thread");
        if(ran) {
        	post.exit(); 
        	Toast.makeText(survey_upload.this, R.string.surveyuploadstopped, Toast.LENGTH_SHORT).show();
        }

    }
	    
	public class PostThread extends Thread{
		
		public Boolean runThread = true;
		
		@Override
		public void run(){
			ran = true;

			while(runThread)
			{
				Log.d(TAG, "Running the thread");
				
				//we need to make sure the gps is trying to get a lock if there are entries which don't have gps loc.
				if(sdb.has_gpsless_entries()) {
					survey_upload.this.startService(new Intent(survey_upload.this,light_loc.class));
				}

				//list all trace files
				sdb.open();
				ArrayList<survey_db_row> sr_list = sdb.fetch_all_completed_entries();
				sdb.close();

				Log.d(TAG, "Points to submit: " + Integer.toString(sr_list.size()));
				Log.d(TAG, "uploading to: " + getString(R.string.surveyuploadurl));
				Log.d(TAG, "version: " + getString(R.string.version));

				for (int i=0; i < sr_list.size(); i++)
				{
					survey_db_row sr = sr_list.get(i);
					File file = null;
					if ((sr.photo_filename != null) && (!sr.photo_filename.toString().equals(""))) {
						Log.d(TAG, "FILENAME: is not null/empty");
						file = new File(sr.photo_filename.toString());
					} else {
						Log.d(TAG, "FILENAME: IS NULL");
					}
					Log.d(TAG, "FILENAME: " + sr.photo_filename);
					try
					{
						if(doPost2(getString(R.string.surveyuploadurl),
								sr.q_int, sr.q_cat, sr.q_sub, sr.q_com,
								sr.longitude, sr.latitude,
								sr.time, sr.version, sr.photo_filename,
								sr.access_token, sr.token_secret,
								sr.request_token))
						{
							if(file != null) {
								file.delete();
							}
							sdb.open();
							sdb.deleteEntry(sr.row_id);
							sdb.close();
						}
					}
					catch (IOException e) 
					{
						// TODO Auto-generated catch block
						Log.d(TAG, "threw an IOException for sending file.");
						e.printStackTrace();
					}

				}
				//we have finished submitting all samples
				
				if(!sdb.has_entries()) {
					stopService(new Intent(survey_upload.this, light_loc.class));

					survey_upload.this.stopSelf();
				} else {
					try {
						Thread.sleep(30*1000);
					} catch (InterruptedException e) {
						// TODO Auto-generated catch block
						e.printStackTrace();
					}
				}
			} 
		}
	
		public void exit()
		{
			runThread = false;
		}
		
		/*
		 * this uses java.net.HttpURLConnection another way to do it is to use apache HttpPost
		 * but the API seems a bit complicated. If you figure out how to use it and its more
		 * efficient then let me know (vids@ucla.edu) Thanks.
		 */
        private boolean doPost2(String url, String q_int, String q_cat, String q_sub, String q_com,
                               String longitude, String latitude, String time,
                               String version, String photo_filename,
                               String access_token, String token_secret,
                               String request_token) throws IOException
        {

            url = "http://stresschill.appspot.com/protected_upload2";

            Log.d(TAG, "Attempting to send file:" + photo_filename);
            Log.d(TAG, "Trying to post: "+url.toString()+" "+photo_filename.toString() + " "+ longitude.toString() + " ...");
            
            if (null == httpClient) {
                httpClient = new DefaultHttpClient();
            }
            HttpPost request = new HttpPost(url.toString());

            if (null == request) {
                return false;
            }
            
            Log.d(TAG, "After Request");

            Log.d(TAG, "COMMENTS: " + q_com);
            
            MultipartEntity entity = new MultipartEntity();
            entity.addPart("stressval", new StringBody(q_int.toString()));
            entity.addPart("category", new StringBody(q_cat.toString()));
            entity.addPart("subcategory", new StringBody(q_sub.toString()));
            entity.addPart("comments", new StringBody(q_com.toString()));
            entity.addPart("longitude", new StringBody(longitude.toString()));
            entity.addPart("latitude", new StringBody(latitude.toString()));
            entity.addPart("time", new StringBody(time.toString()));
            entity.addPart("version", new StringBody(version.toString()));
            entity.addPart("oauth_token", new StringBody(access_token));
            
            Log.d(TAG, "After adding string");

            if (photo_filename == null || photo_filename.equals("")) {
                Log.d(TAG, "ADDING empty string as file contents");
                entity.addPart("file", new StringBody(""));
            } else {
                Log.d(TAG, "ADDING the actual file body of: >>" + photo_filename + "<<");
                File file = new File(photo_filename.toString());
                entity.addPart("file", new FileBody(file));
            }
            
            Log.d(TAG, "After adding file");
            
            request.setEntity(entity);
            
            Log.d(TAG, "After setting entity");
            
            HttpResponse response = httpClient.execute(request);
            
            Log.d(TAG, "Doing HTTP Reqest");

            int status = response.getStatusLine().getStatusCode();
            //Log.d(TAG, generateString(response.getEntity().getContent()));
            Log.d(TAG, "Status Message: "+Integer.toString(status));
            
            if(status == HttpStatus.SC_OK)
            {
                Log.d(TAG, "Sent file.");
                return true;
            }
            else
            {
                Log.d(TAG, "File not sent.");
                return false;
            }
        }
	    private boolean doPost(String url, String q_int, String q_cat, String q_com,
                               String longitude, String latitude, String time,
                               String version,
                               String photo_filename) throws IOException
	    {
	    	Log.d(TAG, "Attempting to send file:" + photo_filename);
	    	Log.d(TAG, "Trying to post: "+url.toString()+" "+photo_filename.toString() + " "+ longitude.toString() + " ...");

            OAuthServiceProvider provider = new OAuthServiceProvider(authenticate.REQUEST_TOKEN_URL,
                                                                     authenticate.AUTHORIZATION_URL,
                                                                     authenticate.ACCESS_TOKEN_URL);
            OAuthConsumer consumer = new OAuthConsumer(authenticate.CALLBACK_URL,
                                                       authenticate.CONSUMER_KEY,
                                                       authenticate.CONSUMER_SECRET,
                                                       provider);
            OAuthAccessor accessor = new OAuthAccessor(consumer);
            OAuthClient client = new OAuthClient(new HttpClient4());

            accessor.requestToken = authenticate.tokens.request_token;
            accessor.accessToken = authenticate.tokens.access_token;
            accessor.tokenSecret = authenticate.tokens.token_secret;

            try {
                ArrayList<Map.Entry<String, String>> params = new ArrayList<Map.Entry<String, String>>();
                params.add(new OAuth.Parameter("stressval", q_int.toString()));
                params.add(new OAuth.Parameter("category", q_cat.toString()));
                params.add(new OAuth.Parameter("comments", q_com.toString()));
                params.add(new OAuth.Parameter("longitude", longitude.toString()));
                params.add(new OAuth.Parameter("latitude", latitude.toString()));
                params.add(new OAuth.Parameter("time", time.toString()));
                params.add(new OAuth.Parameter("version", version.toString()));

                /* pulled from OAuthClient.java:249
                 * OAuthClient.invoke(accessor, null, URL, params); */
                OAuthMessage request_;
                net.oauth.ParameterStyle style;
                {
                    OAuthMessage request = accessor.newRequestMessage(null, authenticate.RESOURCE_URL, params);
                    Object accepted = accessor.consumer.getProperty(OAuthConsumer.ACCEPT_ENCODING);
                    if (accepted != null) {
                        request.getHeaders().add(new OAuth.Parameter(HttpMessage.ACCEPT_ENCODING, accepted.toString()));
                    }
                    Object ps = accessor.consumer.getProperty("parameterStyle");
                    style = (ps == null) ? net.oauth.ParameterStyle.BODY
                            : Enum.valueOf(net.oauth.ParameterStyle.class, ps.toString());

                    request_ = request;
                }

                /* pulled from OAuthClient.java:315
                 * OAuthClient.access() */
                HttpMessage request;
                {
                    HttpMessage httpRequest = HttpMessage.newRequest(request_, style);
                    request = httpRequest;
                }

                /* pulled from WeTap/survey_upload.java:160 and HttpClient4.java:60 */
                Map<String, Object> parameters = client.getHttpParameters();
                HttpResponse response;
                {
                    String CONNECT_TIMEOUT = "connectTimeout";
                    String READ_TIMEOUT = "readTimeout";
                    String FOLLOW_REDIRECTS = "followRedirects";

                    HttpPost httpRequest = new HttpPost(request.url.toExternalForm());

                    for (Map.Entry<String, String> header : request.headers) {
                        httpRequest.addHeader(header.getKey(), header.getValue());
                    }
/*
                    HttpParams params_ = httpRequest.getParams();
                    for (Map.Entry<String, Object> p : parameters.entrySet()) {
                        String name = p.getKey();
                        String value = p.getValue.toString();
                        if (FOLLOW_REDIRECTS.equals(name)) {
                            params_.setBooleanParameter(ClientPNames.HANDLE_REDIRECTS, Boolean.parseBoolean(value));
                        } else if (READ_TIMEOUT.equals(name)) {
                            params_.setIntParameter(CoreConnectionPNames.SO_TIMEOUT, Integer.parseInt(value));
                        } else if (CONNECT_TIMEOUT.equals(name)) {
                            params_.setIntParameter(CoreConnectionPNames.CONNECTION_TIMEOUT, Integer.parseInt(value));
                        }
                    }
*/
                    try {
                        MultipartEntity entity = new MultipartEntity();
                        if (photo_filename == null || photo_filename.equals("")) {
                            Log.d(TAG, "ADDING empty string as file contents");
                            entity.addPart("file", new StringBody(""));
                        } else {
                            Log.d(TAG, "ADDING the actual file body of: >>" + photo_filename + "<<");
                            File file = new File(photo_filename.toString());
                            entity.addPart("file", new FileBody(file));
                        }
                        httpRequest.setEntity(entity);
                    } catch (IOException e) {
                        e.printStackTrace();
                        return false;
                    }

                    HttpClient client_ = new DefaultHttpClient(); //clientPool.getHttpClient(new URL(httpRequest.getURI().toString()));
                    HttpResponse httpResponse = client_.execute(httpRequest);
                    response = httpResponse;
                }

                if (response.getStatusLine().getStatusCode() == HttpStatus.SC_OK) {
                    return true;
                }
            } catch (IOException e) {
                e.printStackTrace();
            } catch (OAuthException e) {
                e.printStackTrace();
            } catch (java.net.URISyntaxException e) {
                e.printStackTrace();
            }

            return false;
	    }
	    
	    public String generateString(InputStream stream) {
  	      InputStreamReader reader = new InputStreamReader(stream);
  	       BufferedReader buffer = new BufferedReader(reader);
  	       StringBuilder sb = new StringBuilder();
  	    
  	       try {
  	           String cur;
  	           while ((cur = buffer.readLine()) != null) {
  	               sb.append(cur + "\n");
  	           }
  	       } catch (IOException e) {
  	           // TODO Auto-generated catch block
  	           e.printStackTrace();
  	       }
  	    
  	       try {
  	           stream.close();
  	       } catch (IOException e) {
  	           // TODO Auto-generated catch block
  	           e.printStackTrace();
  	       }
  	       return sb.toString();
	    }
	    
	    
         /*
          * Read file into String. 
          */
         private String readFileAsString(File file) throws java.io.IOException{
             StringBuilder fileData = new StringBuilder(1024);
             BufferedReader reader = new BufferedReader(new FileReader(file));
             char[] buf = new char[1024];
             int numRead=0;
             while((numRead=reader.read(buf)) != -1){
            	 fileData.append(buf, 0, numRead);
             }
             reader.close();
             return fileData.toString();
         }	
	     
	    
	}

}
