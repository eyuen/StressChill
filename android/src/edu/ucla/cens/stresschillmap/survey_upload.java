package edu.ucla.cens.stresschillmap;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.FilenameFilter;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;

import org.apache.http.HttpResponse;
import org.apache.http.HttpStatus;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.mime.MultipartEntity;
import org.apache.http.entity.mime.content.FileBody;
import org.apache.http.entity.mime.content.StringBody;
import org.apache.http.impl.client.DefaultHttpClient;

import android.app.Activity;
import android.app.Service;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.IBinder;
import android.util.Log;
import android.widget.Toast;

import edu.ucla.cens.stresschillmap.survey_db;
import edu.ucla.cens.stresschillmap.survey_db.survey_db_row;

public class survey_upload extends Service{
    private survey_db sdb;
    private SharedPreferences preferences;

	PostThread post;
	private static final String TAG = "SurveyUploadThread";

    
    @Override
    public void onCreate() {
        preferences = getSharedPreferences(getString(R.string.preferences), Activity.MODE_PRIVATE);
        /* XXX temporarily allow unauthorized upload... (testing and stuff)
        if (!preferences.getBoolean("authenticated", false)) {
            Log.d(TAG, "user is not authenticated... stopping this service");
            return;
        }
        */

		sdb = new survey_db(this);

        Toast.makeText(this, R.string.surveyuploadstarted, Toast.LENGTH_SHORT).show();

    	post = new PostThread();
    	post.start();
    }

	@Override
	public IBinder onBind(Intent arg0) {
		// TODO Auto-generated method stub
		return null;
	}
	
    @Override
    public void onDestroy() {
        Toast.makeText(this, R.string.surveyuploadstopped, Toast.LENGTH_SHORT).show();
        Log.d(TAG, "Stopping the thread");
        post.exit();
    }
	    
	public class PostThread extends Thread{
		
		public Boolean runThread = true;
		
		private class PicFiles implements FilenameFilter{
			public boolean accept(File file, String name) {
				return (name.endsWith(".jpg"));
			}	
		}
		
		public void run(){

			try {
				while(runThread)
				{
					this.sleep(10000);
					Log.d(TAG, "Running the thread");

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
							if(doPost(getString(R.string.surveyuploadurl),
                                      sr.q_int, sr.q_cat,
                                      sr.longitude, sr.latitude,
                                      sr.time, sr.version, sr.photo_filename))
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
						this.sleep(1000);
					}
				} 
			}
			catch (InterruptedException e) 
			{
				// TODO Auto-generated catch block
				e.printStackTrace();
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
	    private boolean doPost(String url, String q_int, String q_cat,
                               String longitude, String latitude, String time,
                               String version,
                               String photo_filename) throws IOException
	    {
	    	Log.d(TAG, "Attempting to send file:" + photo_filename);
	    	Log.d(TAG, "Trying to post: "+url.toString()+" "+photo_filename.toString() + " "+ longitude.toString() + " ...");
	    	
	    	HttpClient httpClient = authenticate.httpClient;
			if (null == httpClient) {
				httpClient = new DefaultHttpClient();
			}
	    	HttpPost request = new HttpPost(url.toString());

			if (null == request) {
				return false;
			}
	    	
	    	Log.d(TAG, "After Request");
	    	
	    	MultipartEntity entity = new MultipartEntity();
	    	entity.addPart("stressval", new StringBody(q_int.toString()));
	    	entity.addPart("category", new StringBody(q_cat.toString()));
            entity.addPart("longitude", new StringBody(longitude.toString()));
            entity.addPart("latitude", new StringBody(latitude.toString()));
            entity.addPart("time", new StringBody(time.toString()));
            entity.addPart("version", new StringBody(version.toString()));
	    	
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
