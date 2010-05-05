package edu.ucla.cens.stresschillmap;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Map;

import net.oauth.OAuth;
import net.oauth.OAuthAccessor;
import net.oauth.OAuthConsumer;
import net.oauth.OAuthException;
import net.oauth.OAuthMessage;
import net.oauth.OAuthServiceProvider;
import net.oauth.client.OAuthClient;
import net.oauth.client.OAuthResponseMessage;
import net.oauth.client.httpclient4.HttpClient4;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
import android.app.ProgressDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Looper;
import android.util.Log;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;

public class authenticate extends Activity implements Runnable {
    private Context ctx;
    private EditText et_pass;
    private EditText et_user;
    private CheckBox cb_save_login;

    private String user = "";
    private String pass1 = "";
    private Button submit;
    private Button reg;
    private boolean save_login = false;

    private static final int LOGIN = 0;
    private static final int REGISTER = 1;
    private int auth_type = LOGIN;

    private static final String TAG = "Authentication";
    private static final int DIALOG_PROGRESS = 1;

    private SharedPreferences preferences;
    private ProgressDialog mProgressDialog;
    private String error_message = "Authentication failure. Please go back and try again.";

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
        et_pass = (EditText) findViewById(R.id.password);
        et_user = (EditText) findViewById(R.id.user_input);
        cb_save_login = (CheckBox) findViewById(R.id.save_login);
        submit = (Button) findViewById(R.id.login);
        reg = (Button) findViewById(R.id.register);
        ctx = authenticate.this;

        tokens = new token_store();

        Log.d(TAG, "started authenticate intent");

        preferences = this.getSharedPreferences(getString(R.string.preferences), Activity.MODE_PRIVATE);
        preferences.edit().putBoolean("authenticated", false)
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
        
        submit.setOnClickListener(new View.OnClickListener() {
            public void onClick (View view) {
                auth_type = LOGIN;
                user = et_user.getText().toString();
                pass1 = et_pass.getText().toString();
                save_login = cb_save_login.isChecked();
                Intent i = new Intent(ctx, authenticate.class);

                if (save_login) {
                    preferences.edit().putString("user", user)
                                      .putString("pass", pass1)
                                      .putBoolean("save_login", save_login)
                                      .commit();
                } else {
                    preferences.edit().putString("user", "")
                                      .putString("pass", "")
                                      .putBoolean("save_login", false)
                                      .commit();
                }

                showDialog (DIALOG_PROGRESS);
                Thread thread = new Thread(authenticate.this);
                thread.start();
            }
        });

        reg.setOnClickListener(new View.OnClickListener() {
            public void onClick (View view) {
                Context ctx = authenticate.this;
                Intent i = new Intent (ctx, register.class);
                ctx.startActivity (i);
            }
        });
	}


  @Override
  public boolean onCreateOptionsMenu (Menu m) {
    super.onCreateOptionsMenu (m);

    m.add (Menu.NONE, 0, Menu.NONE, "Instructions").setIcon (android.R.drawable.ic_menu_help);
    m.add (Menu.NONE, 1, Menu.NONE, "About").setIcon (android.R.drawable.ic_menu_info_details);
    return true;
  }
  
  @Override
  public boolean onOptionsItemSelected (MenuItem index) {
    Context ctx = authenticate.this;
    Intent i;
    switch (index.getItemId()) {
      case 0:
        i = new Intent (ctx, instructions.class);
        break;
      case 1:
        i = new Intent (ctx, about.class);
        break;
      default:
        return false;
    }
    ctx.startActivity (i);
    return true;
  }


    /* user : plain text,
     * pass : plaintext password */
    private boolean login_user (String user, String pass) {
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
        Log.d(TAG, "login_user(): failed to login");
        return false;
    }

    private token_store get_access_token_hack(String user, String pass) {
        if (null == user || user.equals("")) {
            error_message = "Empty or missing username";
            Log.d(TAG, "Authentication failure: " + error_message);
            return null;
        }

        if (null == pass || pass.equals("")) {
            error_message = "Empty or missing password";
            Log.d(TAG, "Authentication failure: " + error_message);
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
                error_message = generateString(((OAuthResponseMessage)message).getHttpResponse().getBody());
                Log.d(TAG, "Authentication failure: " + error_message);
                return null;
            }
            access_token = message.getParameter("oauth_token");
            access_token_secret = message.getParameter("oauth_token_secret");
        } catch (IOException e) {
            error_message = "Got IOException. Check your connection and try again";
            Log.d(TAG, "Authentication failure: " + error_message);
            e.printStackTrace();
            return null;
        } catch (OAuthException e) {
            /* FIXME: instead of returning a message with status code 401,
             * client.invoke() throws this exception... */
            error_message = "Got OAuthException. Check your connection and try again";
            Log.d(TAG, "Authentication failure: " + error_message);
            error_message = "Invalid username or password. Please go back and try again.";
            e.printStackTrace();
            return null;
        } catch (java.net.URISyntaxException e) {
            error_message = "Got URISyntaxException. Check your connection and try again";
            Log.d(TAG, "Authentication failure: " + error_message);
            e.printStackTrace();
            return null;
        }

        ts.access_token = access_token;
        ts.token_secret = access_token_secret;
        ts.request_token = "";

        error_message = "Successfully authenticated!";
        return ts;
    }

    private token_store get_access_token_properly(String user, String pass) {
        if (null == user || null == pass) {
            error_message = "Invalid or missing username/password";
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
                    error_message = generateString(((OAuthResponseMessage)message).getHttpResponse().getBody());
                    return null;
                }
                // "6.1.2.  Service Provider Issues an Unauthorized Request Token"
                request_token = message.getParameter("oauth_token");
                String callback_confirmed = message.getParameter("oauth_callback_confirmed");
                if (!callback_confirmed.equals("true")) {
                    Log.d(TAG, "SERVICE PROVIDER FAILED TO CONFIRM THE CALLBACK");
                }
            } catch (IOException e) {
                error_message = "IOException";
                Log.d(TAG, "IOException");
                e.printStackTrace();
                return null;
            } catch (OAuthException e) {
                error_message = "OAuthException";
                Log.d(TAG, "OAuthException");
                e.printStackTrace();
                return null;
            } catch (java.net.URISyntaxException e) {
                error_message = "URISyntaxException";
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
                    error_message = generateString(((OAuthResponseMessage)message).getHttpResponse().getBody());
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
                error_message = "IOException";
                Log.d(TAG, "IOException");
                e.printStackTrace();
            } catch (OAuthException e) {
                error_message = "OAuthException";
                Log.d(TAG, "OAuthException");
                e.printStackTrace();
            } catch (java.net.URISyntaxException e) {
                error_message = "URISyntaxException";
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
                    error_message = generateString(((OAuthResponseMessage)message).getHttpResponse().getBody());
                    return null;
                }
                // "6.3.2.  Service Provider Grants an Access Token"
                access_token = message.getParameter("oauth_token");
                access_token_secret = message.getParameter("oauth_token_secret");
            } catch (IOException e) {
                error_message = "IOException";
                Log.d(TAG, "IOException");
                e.printStackTrace();
            } catch (OAuthException e) {
                error_message = "OAuthException";
                Log.d(TAG, "OAuthException");
                e.printStackTrace();
            } catch (java.net.URISyntaxException e) {
                error_message = "URISyntaxException";
                Log.d(TAG, "java.net.URISyntaxException");
                e.printStackTrace();
            }

            Log.d(TAG, "step 2.2: obtain an access token...");
            Log.d(TAG, "access_token: " + access_token.toString());
            Log.d(TAG, "access_token_secret: " + access_token_secret.toString());
        }

        if (access_token.equals("")) {
            error_message = "Unable to get access tokens";
            return null;
        }

        ts.access_token = access_token;
        ts.token_secret = access_token_secret;
        ts.request_token = request_token;
        error_message = "Successfully authenticated!";

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
            error_message = "sha1sum failure";
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

        if (true == auth()) {
            ctx.startActivity(new Intent(ctx, home.class));
            Log.d(TAG, "started survey intent");
            authenticate.this.finish();
            mProgressDialog.dismiss();
        } else {
            mProgressDialog.dismiss();
            Log.d(TAG, "handler(): login failed... calling auth_failed()");
            auth_failed();
        }

        Looper.loop();
    }

    private boolean auth() {
        if (login_user (user, pass1)) {
            preferences.edit().putBoolean("authenticated", true).commit();
            Log.d(TAG, "auth(): login_user(): successfully logged user in");
            return true;
        }

        Log.d(TAG, "auth(): failed to authenticate (create account / login)");
        return false;
    }

    private void auth_failed() {
        Log.d(TAG, "auth was a failure");
        final AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("Could not login")
            .setMessage(error_message)
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
