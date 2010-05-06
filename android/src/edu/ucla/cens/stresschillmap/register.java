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
import android.view.Menu;
import android.view.MenuItem;

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

public class register extends Activity implements Runnable {
  private Context ctx;
  private EditText et_email;
  private EditText et_pass;
  private EditText et_pass2;
  private EditText et_user;
  private EditText et_classid;

  private String email = "";
  private String user = "";
  private String pass1 = "";
  private String pass2 = "";
  private String classid = "";
  private Button submit;

  private static final int LOGIN = 0;
  private static final int REGISTER = 1;
  private int auth_type = REGISTER;

  private static final String TAG = "Register";
  private static final int DIALOG_PROGRESS = 1;

  private SharedPreferences preferences;
  private ProgressDialog mProgressDialog;
  private String error_message = "Registration failure. Please go back and try again.";

  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    setContentView(R.layout.register);
    et_email = (EditText) findViewById(R.id.email);
    et_pass = (EditText) findViewById(R.id.password);
    et_pass2 = (EditText) findViewById(R.id.password2);
    et_user = (EditText) findViewById(R.id.user_input);
    et_classid = (EditText) findViewById(R.id.classid_et);
    submit = (Button) findViewById(R.id.login);
    ctx = register.this;

    Log.d(TAG, "started registe intent");

    preferences = this.getSharedPreferences(getString(R.string.preferences), Activity.MODE_PRIVATE);
    Log.d(TAG, "set initial auth state to false");

    submit.setOnClickListener(new View.OnClickListener() {
      public void onClick (View view) {
        auth_type = REGISTER;
        email = et_email.getText().toString();
        pass2 = et_pass2.getText().toString();
        user = et_user.getText().toString();
        pass1 = et_pass.getText().toString();
        classid = et_classid.getText().toString();
        Intent i = new Intent(ctx, register.class);


        showDialog (DIALOG_PROGRESS);
        Thread thread = new Thread(register.this);
        thread.start();
      }
    });
  }

  @Override
  public boolean onCreateOptionsMenu (Menu m) {
    super.onCreateOptionsMenu (m);

    m.add (Menu.NONE, 0, Menu.NONE, "Instructions").setIcon (android.R.drawable.ic_menu_help);
    m.add (Menu.NONE, 0, Menu.NONE, "About").setIcon (android.R.drawable.ic_menu_info_details);
    return true;
  }

  @Override
  public boolean onOptionsItemSelected (MenuItem index) {
    Context ctx = register.this;
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

  private boolean register_user (String email, String user, String pass1, String pass2, String classid) {
    String stored_pass_hash = preferences.getString(user + "_un", "");
    if (stored_pass_hash.equals("")) {
      if (!pass1.equals(pass2)) {
        error_message = "The passwords you entered do not match";
        Log.d(TAG, "Registration failure: " + error_message);
        return false;
      }

      Log.d(TAG, "registering new account: " + user);
      HttpClient httpClient = new DefaultHttpClient();
      HttpPost request = new HttpPost(getString(R.string.register_user));

      try {
        MultipartEntity entity = new MultipartEntity();
        entity.addPart("username", new StringBody(user));
        entity.addPart("password", new StringBody(pass1));
        entity.addPart("confirmpassword", new StringBody(pass2));
        entity.addPart("email", new StringBody(email));
        entity.addPart("classid", new StringBody(classid));
        request.setEntity(entity);
      } catch (UnsupportedEncodingException e) {
        error_message = "Error formatting registration message";
        Log.d(TAG, "Registration failure: " + error_message);
        e.printStackTrace();
        return false;
      }

      try {
        HttpResponse response = httpClient.execute(request);
        Log.d(TAG, "Doing AppSpot HTTPS Request");
        int status = response.getStatusLine().getStatusCode();
        error_message = generateString(response.getEntity().getContent());
        if (HttpStatus.SC_OK != status) {
          Log.d(TAG, "got status: " + status);
          Log.d(TAG, "Register failure: " + error_message);
          return false;
        }
      } catch (IOException e) {
        e.printStackTrace();
        error_message = "Error connecting to registration server";
        Log.d(TAG, "Registration failure: " + error_message);
        return false;
      }
      return true;
    } else {
      error_message = "An account with this username already exists";
      Log.d(TAG, "Registration failure: " + error_message);
    }
    return false;
  }

  @Override
  protected Dialog onCreateDialog(int id) {
    switch (id) {
      case DIALOG_PROGRESS:
        mProgressDialog = new ProgressDialog(register.this);
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
      mProgressDialog.dismiss();
      final AlertDialog.Builder builder = new AlertDialog.Builder(this);
      builder.setTitle("Successfully registered!")
             .setMessage("You can now return to the login page and login.")
             .setCancelable(false)
             .setPositiveButton("Return", new DialogInterface.OnClickListener() {
                public void onClick(final DialogInterface dialog, final int id) {
                  Log.d(TAG, "handler(): registered successfully");
                  ctx.startActivity(new Intent(ctx, authenticate.class));
                }
              });
      final AlertDialog alert = builder.create();
      alert.show();
    } else {
      mProgressDialog.dismiss();
      Log.d(TAG, "handler(): register failed");
      Log.d(TAG, "handler(): auth failed... calling auth_failed()");
      auth_failed();
    }
    Looper.loop();
  }

  private boolean auth() {
    if (register_user (email, user, pass1, pass2, classid)) {
      Log.d(TAG, "auth(): register_user(): successfully created a new account");
      return true;
    }

    Log.d(TAG, "auth(): failed to create account");
    return false;
  }

  private void auth_failed() {
    Log.d(TAG, "auth was a failure");
    final AlertDialog.Builder builder = new AlertDialog.Builder(this);
    builder.setTitle("Could not register")
           .setMessage(error_message)
           .setCancelable(false)
           .setPositiveButton("Go back", new DialogInterface.OnClickListener() {
             public void onClick(final DialogInterface dialog, final int id) {
               ctx.startActivity(new Intent(ctx, register.class));
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
