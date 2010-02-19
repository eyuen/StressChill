package edu.ucla.cens.stresschillmap;

import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.BufferedReader;

import org.apache.http.HttpResponse;
import org.apache.http.HttpStatus;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.mime.MultipartEntity;
import org.apache.http.impl.client.DefaultHttpClient;
import org.apache.http.entity.mime.content.StringBody;


import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
import android.app.ProgressDialog;

import android.content.DialogInterface;
import android.content.DialogInterface.OnClickListener;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.Context;

import android.view.View;
import android.widget.TextView;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.Button;
import android.widget.Toast;

import android.os.Bundle;
import android.os.Handler;
import android.os.Message;
import android.os.Looper;
import android.util.Log;

import android.net.Uri;

import java.util.*;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

import net.oauth.OAuth;
import net.oauth.OAuthAccessor;
import net.oauth.OAuthConsumer;
import net.oauth.OAuthServiceProvider;
import net.oauth.OAuthException;
import net.oauth.OAuthMessage;
import net.oauth.OAuthProblemException;
import net.oauth.client.OAuthClient;
import net.oauth.client.OAuthResponseMessage;
import net.oauth.client.httpclient4.HttpClient4;

public class authenticate extends Activity implements Runnable {
    private Context ctx;
    private TextView tv_email;
    private EditText et_email;
    private EditText et_pass;
    private TextView tv_pass2;
    private EditText et_pass2;
    private EditText et_user;
    private CheckBox cb_save_login;
    private CheckBox cb_register;

    private String email = "";
    private String user = "";
    private String pass1 = "";
    private String pass2 = "";
    private Button submit;
    private boolean save_login = false;

    private static final int LOGIN = 0;
    private static final int REGISTER = 1;
    private int auth_type = LOGIN;

	private static final String TAG = "Authentication";
    private static final int DIALOG_PROGRESS = 1;

    private SharedPreferences preferences;
    private ProgressDialog mProgressDialog;
    private String auth_fail_string = "login";

    public static String REQUEST_TOKEN_URL = "https://stresschill.appspot.com/request_token";
    public static String ACCESS_TOKEN_URL = "https://stresschill.appspot.com/access_token";
    public static String AUTHORIZATION_URL = "https://stresschill.appspot.com/authorize";
    public static String HACK_AUTHORIZATION_URL = "https://stresschill.appspot.com/authorize_access";
    public static String CALLBACK_URL = "http://printer.example.com/request_token_ready";
    public static String RESOURCE_URL = "http://stresschill.appspot.com/protected_upload";

    public static final String CONSUMER_KEY = "Tq5YzEAjm55bt3pb";
    public static final String CONSUMER_SECRET = "UMy9WYPDR4armmHr";

    public static token_store tokens;

    public class token_store {
        public String access_token;
        public String token_secret;
        public String request_token;

        token_store() {
            access_token = "";
            token_secret = "";
            request_token = "";
        }
    }

	@Override
	protected void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);
        setContentView(R.layout.authenticate);
        tv_email = (TextView) findViewById(R.id.tv1);
        et_email = (EditText) findViewById(R.id.email);
        et_pass = (EditText) findViewById(R.id.password);
        tv_pass2 = (TextView) findViewById(R.id.pass2_label);
        et_pass2 = (EditText) findViewById(R.id.password2);
        et_user = (EditText) findViewById(R.id.user_input);
        cb_register = (CheckBox) findViewById(R.id.cb_register);
        cb_save_login = (CheckBox) findViewById(R.id.save_login);
        submit = (Button) findViewById(R.id.login);
        ctx = authenticate.this;

        tokens = new token_store();

        Log.d(TAG, "started authenticate intent");

        preferences = this.getSharedPreferences(getString(R.string.preferences), Activity.MODE_PRIVATE);
        preferences.edit().putBoolean("authenticated", false)
                          .putBoolean("registered", false)
                          .commit();
        Log.d(TAG, "set initial auth state to false");

        user = preferences.getString("user", "");
        pass1 = preferences.getString("pass", "");
        save_login = preferences.getBoolean("save_login", false);

        if (!user.equals("") && !pass1.equals("") && save_login) {
            Log.d(TAG, "SETTING VALUES");
            et_user.setText(user);
            et_pass.setText(pass1);
            cb_save_login.setChecked(save_login);
        }
        
        cb_register.setOnClickListener(register_check_box);

        submit.setOnClickListener(new View.OnClickListener() {
            public void onClick (View view) {
                auth_type = LOGIN;
                if (cb_register.isChecked()) {
                    auth_type = REGISTER;
                    email = et_email.getText().toString();
                    pass2 = et_pass2.getText().toString();
                }
                user = et_user.getText().toString();
                pass1 = et_pass.getText().toString();
                save_login = cb_save_login.isChecked();
                Intent i = new Intent(ctx, authenticate.class);

                if (save_login) {
                    preferences.edit().putString("user", user)
                                      .putString("pass", pass1)
                                      .putBoolean("save_login", save_login)
                                      .commit();
                }

                showDialog (DIALOG_PROGRESS);
                Thread thread = new Thread(authenticate.this);
                thread.start();
            }
        });
	}

    private boolean register_user (String email, String user, String pass1, String pass2) {
        String stored_pass_hash = preferences.getString(user + "_un", "");
        if (stored_pass_hash.equals("")) {
            if (!pass1.equals(pass2)) {
                Toast.makeText(ctx, "the passwords you entered do not match", Toast.LENGTH_LONG).show();
                return false;
            }

            Log.d(TAG, "registering new account: " + user + ", " + pass1);
            HttpClient httpClient = new DefaultHttpClient();
            HttpPost request = new HttpPost(getString(R.string.register_user));

            try {
                MultipartEntity entity = new MultipartEntity();
                entity.addPart("username", new StringBody(user));
                entity.addPart("password", new StringBody(pass1));
                entity.addPart("confirmpassword", new StringBody(pass2));
                entity.addPart("email", new StringBody(email));
                request.setEntity(entity);
            } catch (UnsupportedEncodingException e) {
                e.printStackTrace();
                return false;
            }

            try {
                HttpResponse response = httpClient.execute(request);
                Log.d(TAG, "Doing AppSpot HTTPS Request");
                int status = response.getStatusLine().getStatusCode();
                if (HttpStatus.SC_OK != status) {
                    Log.d(TAG, "got status: " + status);
                    Log.d(TAG, generateString(response.getEntity().getContent()));
                    return false;
                }
            } catch (IOException e) {
                e.printStackTrace();
                return false;
            }
            return true;
        } else {
            Toast.makeText(ctx, "an account with this username already exists", Toast.LENGTH_LONG);
        }
        return false;
    }

    /* user : plain text,
     * pass : plaintext password */
    private boolean login_user (String user, String pass) {
        Log.d(TAG, "login_user (String user, String pass) = " + user + ", " + pass + ".");
        String stored_pass = preferences.getString(user + "_un", "");

        if (stored_pass.equals("")) {
            /* login using the internet and our oauth consumer stuff */
            tokens = get_access_token_hack(user, pass);
            if (null == tokens) {
                Log.d(TAG, "couldnt get access token properly");
                return false;
            }
            Log.d(TAG, "got access token!!");

            /* if oauth login was successful then add this user to the db */
            preferences.edit().putString(user + "_un", pass)
                              .putString(user + "_at", tokens.access_token)
                              .putString(user + "_ts", tokens.token_secret)
                              .putString(user + "_rt", tokens.request_token)
                              .commit();
            return true;
        } else if (stored_pass.equals(pass)) {
            Log.d(TAG, "stored pass == submitted pass");
            tokens.access_token = preferences.getString(user + "_at", "");
            tokens.token_secret = preferences.getString(user + "_ts", "");
            tokens.request_token = preferences.getString(user + "_rt", "");
            return true;
        }
        return false;
    }

    android.view.View.OnClickListener register_check_box = new android.view.View.OnClickListener() {
        public void onClick(View v) {
            CheckBox cb = (CheckBox) v;
            int state = cb.isChecked() ? 0 : android.view.View.INVISIBLE;
            tv_email.setVisibility(state);
            et_email.setVisibility(state);
            tv_pass2.setVisibility(state);
            et_pass2.setVisibility(state);
            if (cb.isChecked()) {
                submit.setText("Register");
            } else {
                submit.setText("Login");
            }
        }
    };

    private token_store get_access_token_hack(String user, String pass) {
        if (null == user || user.equals("")
            || null == pass || pass.equals(""))
        {
            return null;
        }

        String access_token = "";
        String access_token_secret = "";
        token_store ts = new token_store();

        OAuthServiceProvider provider = new OAuthServiceProvider(REQUEST_TOKEN_URL, HACK_AUTHORIZATION_URL, ACCESS_TOKEN_URL);
        OAuthConsumer consumer = new OAuthConsumer(CALLBACK_URL, CONSUMER_KEY, CONSUMER_SECRET, provider);
        OAuthAccessor accessor = new OAuthAccessor(consumer);
        OAuthClient client = new OAuthClient(new HttpClient4());

        ArrayList<Map.Entry<String, String>> params = new ArrayList<Map.Entry<String, String>>();
        params.add(new OAuth.Parameter("username", user));
        params.add(new OAuth.Parameter("password", sha1sum(pass).toString()));
        params.add(new OAuth.Parameter("oauth_callback", CALLBACK_URL));
        
        try {
            OAuthMessage message = client.invoke(accessor, null, HACK_AUTHORIZATION_URL, params);
            if (((OAuthResponseMessage)message).getHttpResponse().getStatusCode() != 200) {
                return null;
            }
            access_token = message.getParameter("oauth_token");
            access_token_secret = message.getParameter("oauth_token_secret");
        } catch (IOException e) {
            e.printStackTrace();
            return null;
        } catch (OAuthException e) {
            e.printStackTrace();
            return null;
        } catch (java.net.URISyntaxException e) {
            e.printStackTrace();
            return null;
        }

        ts.access_token = access_token;
        ts.token_secret = access_token_secret;
        ts.request_token = "";
        return ts;
    }

    private token_store get_access_token_properly(String user, String pass) {
        if (null == user || null == pass) {
            return null;
        }

        token_store ts = new token_store();

        // step 2: acquire a request token "6.1.1.  Consumer Obtains a Request Token"
        OAuthServiceProvider provider = new OAuthServiceProvider(REQUEST_TOKEN_URL, AUTHORIZATION_URL, ACCESS_TOKEN_URL);
        OAuthConsumer consumer = new OAuthConsumer(CALLBACK_URL, CONSUMER_KEY, CONSUMER_SECRET, provider);
        OAuthAccessor accessor = new OAuthAccessor(consumer);
        OAuthClient client = new OAuthClient(new HttpClient4());
        String request_token = "";

        {
            try {
                ArrayList<Map.Entry<String, String>> params = new ArrayList<Map.Entry<String, String>>();
                params.add(new OAuth.Parameter("oauth_callback", CALLBACK_URL));
                OAuthMessage message = client.getRequestTokenResponse(accessor, null, params);
                if (((OAuthResponseMessage)message).getHttpResponse().getStatusCode() != 200) {
                    return null;
                }
                // "6.1.2.  Service Provider Issues an Unauthorized Request Token"
                request_token = message.getParameter("oauth_token");
                String callback_confirmed = message.getParameter("oauth_callback_confirmed");
                if (!callback_confirmed.equals("true")) {
                    Log.d(TAG, "SERVICE PROVIDER FAILED TO CONFIRM THE CALLBACK");
                }
            } catch (IOException e) {
                Log.d(TAG, "IOException");
                e.printStackTrace();
                return null;
            } catch (OAuthException e) {
                Log.d(TAG, "OAuthException");
                e.printStackTrace();
                return null;
            } catch (java.net.URISyntaxException e) {
                Log.d(TAG, "java.net.URISyntaxException");
                e.printStackTrace();
                return null;
            }
            Log.d(TAG, "step 2: acquire a request token");
            Log.d(TAG, "request_token: " + request_token.toString());
        }

        // step:2.1 authorize the request token ... "6.2.1. Consumer Directs the User to the Service Provider"
        String verifier = "";
        {
            String username = user;
            String hash_password = sha1sum (pass);

            // see:
            // http://java.sun.com/j2se/1.4.2/docs/api/java/security/MessageDigest.html#getInstance(java.lang.String)
            // http://java.sun.com/j2se/1.4.2/docs/guide/security/CryptoSpec.html#AppA
            ArrayList<Map.Entry<String, String>> params = new ArrayList<Map.Entry<String, String>>();
            params.add(new OAuth.Parameter("username", username));
            params.add(new OAuth.Parameter("password", hash_password.toString()));
            params.add(new OAuth.Parameter("oauth_callback", CALLBACK_URL));
            params.add(new OAuth.Parameter("oauth_token", request_token));

            try {
                OAuthMessage message = client.invoke(accessor, "GET", accessor.consumer.serviceProvider.userAuthorizationURL, params);
                if (((OAuthResponseMessage)message).getHttpResponse().getStatusCode() != 200) {
                    return null;
                }
                String response = message.readBodyAsString();
                Log.d(TAG, "response: " + response);
                String key = "oauth_verifier=";
                verifier = response.substring(response.indexOf(key)+key.length()).split("&")[0];
                // "6.2.3.  Service Provider Directs the User Back to the Consumer"
                //String new_request_token = message.getParameter("oauth_token");
                //if (null == new_request_token || !new_request_token.equals(request_token)) {
                //    Log.d(TAG, "REQUEST TOKEN RECEIVED FROM USER/PROVIDER DID NOT MATCH");
                //}
            } catch (IOException e) {
                Log.d(TAG, "IOException");
                e.printStackTrace();
            } catch (OAuthException e) {
                Log.d(TAG, "OAuthException");
                e.printStackTrace();
            } catch (java.net.URISyntaxException e) {
                Log.d(TAG, "java.net.URISyntaxException");
                e.printStackTrace();
            }

            Log.d(TAG, "step 2.1: authorize the request token...");
            Log.d(TAG, "username: " + username);
            Log.d(TAG, "password: " + hash_password.toString());
            Log.d(TAG, "verifier: " + verifier);
        }

        // step:2.2 obtain an access token ... "6.3.1.  Consumer Requests an Access Token"
        String access_token = "";
        String access_token_secret = "";
        {
            ArrayList<Map.Entry<String, String>> params = new ArrayList<Map.Entry<String, String>>();
            params.add(new OAuth.Parameter("oauth_verifier", verifier));

            try {
                OAuthMessage message = client.getAccessToken(accessor, null, params);
                if (((OAuthResponseMessage)message).getHttpResponse().getStatusCode() != 200) {
                    return null;
                }
                // "6.3.2.  Service Provider Grants an Access Token"
                access_token = message.getParameter("oauth_token");
                access_token_secret = message.getParameter("oauth_token_secret");
            } catch (IOException e) {
                Log.d(TAG, "IOException");
                e.printStackTrace();
                    } catch (OAuthException e) {
                Log.d(TAG, "OAuthException");
                e.printStackTrace();
            } catch (java.net.URISyntaxException e) {
                Log.d(TAG, "java.net.URISyntaxException");
                e.printStackTrace();
            }

            Log.d(TAG, "step 2.2: obtain an access token...");
            Log.d(TAG, "access_token: " + access_token.toString());
            Log.d(TAG, "access_token_secret: " + access_token_secret.toString());
        }

        if (access_token.equals("")) {
            return null;
        }

        ts.access_token = access_token;
        ts.token_secret = access_token_secret;
        ts.request_token = request_token;

        return ts;
    }

    private String sha1sum (String text) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-1");
            byte hash[] = md.digest(text.getBytes());
            StringBuffer hexString = new StringBuffer("");
            for (int i = 0; i < hash.length; i++) {
                String hex = Integer.toHexString(0xFF & hash[i]);
                if (1 == hex.length()) {
                    hexString.append('0');
                }
                hexString.append(hex);
            }
            return hexString.toString();
        } catch (NoSuchAlgorithmException e) {
            e.printStackTrace();
            return null;
        }
    }

    @Override
    protected Dialog onCreateDialog(int id) {
        switch (id) {
        case DIALOG_PROGRESS:
            mProgressDialog = new ProgressDialog(authenticate.this);
            mProgressDialog.setTitle("Working...");
            mProgressDialog.setMessage("Authenticating StressChill...");
            mProgressDialog.setProgressStyle(ProgressDialog.STYLE_SPINNER);
            return mProgressDialog;
        }
        return null;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if(mProgressDialog != null) {
            dismissDialog(DIALOG_PROGRESS);
            mProgressDialog = null;
        }
    }

    public void run() {
        Looper.prepare();
        Message msg = new Message();
        Bundle b = new Bundle();

        b.putBoolean("authenticated", auth());
        msg.setData(b);

        handler.sendMessage(msg);
        handler.sendEmptyMessage(0);
        Looper.loop();
    }

    private Handler handler = new Handler() {
        @Override
        public void handleMessage(Message msg) {
            mProgressDialog.dismiss();
            switch (auth_type) {
                case LOGIN:
                    if(msg.getData().getBoolean("authenticated")) {
                        ctx.startActivity(new Intent(ctx, home.class));
                        Log.d(TAG, "started survey intent");
                        startService(new Intent(ctx, survey_upload.class));
                        Log.d(TAG, "started survey upload intent");
                        authenticate.this.finish();
                        return;
                    } else {
                        auth_fail_string = "login";
                    }
                    break;
                case REGISTER:
                    if (msg.getData().getBoolean("registered")) {
                        ctx.startActivity(new Intent(ctx, authenticate.class));
                        authenticate.this.finish();
                        return;
                    } else {
                        auth_fail_string = "register";
                    }
                    break;
                default:
                    auth_failed();
            }
            auth_failed();
        }
    };

    private boolean auth() {
        if (cb_register.isChecked()) {
            if (register_user (email, user, pass1, pass2)) {
                preferences.edit().putBoolean("registered", true).commit();
                return true;
            }
        } else if (login_user (user, pass1)) {
            preferences.edit().putBoolean("authenticated", true).commit();
            return true;
        }

        return false;
    }

    private void auth_failed() {
        Log.d(TAG, "auth was a failure");
        final AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("Could not " + auth_fail_string)
            .setMessage("You must enter valid credentials before you can proceed.")
            .setCancelable(false)
            .setPositiveButton("Go back", new DialogInterface.OnClickListener() {
                public void onClick(final DialogInterface dialog, final int id) {
                    ctx.startActivity(new Intent(ctx, authenticate.class));
                    authenticate.this.finish();
                }
            });
        final AlertDialog alert = builder.create();
        alert.show();
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
}
