package edu.ucla.cens.stresschillmap;

import java.util.List;
import java.util.ArrayList;

import java.io.OutputStream;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;

import java.util.Date;
import java.net.URI;
import java.net.URISyntaxException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.IOException;
import java.io.BufferedReader;

import org.apache.http.HttpResponse;
import org.apache.http.client.ClientProtocolException;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.DefaultHttpClient;

import org.json.JSONException;
import org.json.JSONObject;

import android.app.Activity;

import android.os.Bundle;

import android.content.SharedPreferences;

import android.view.View;
import android.webkit.WebView;
import android.widget.TextView;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;

import android.util.Log;




public class popup extends Activity {
    String TAG = "POPUP";
    @Override
    public void onCreate (Bundle b) {
        super.onCreate (b);
        setContentView (R.layout.popup);

        SharedPreferences perf = this.getSharedPreferences(getString(R.string.preferences), Activity.MODE_PRIVATE);
        String req_key = perf.getString("site_key", "");

        String photo = "";
        String stressval = "0";
        String category = "Not provided"; 
        String subcategory = "None";
        String comments = "";

        if (req_key != null && req_key != "") {
            String site_url = getString(R.string.map_full_point) + "?key=" + req_key;
            
            String site_data = getUrlData (site_url);

            Log.d(TAG, "THE SITE URL: " + site_url);

            JSONObject entry;
            try { entry = new JSONObject (site_data.toString()); }
            catch (JSONException e) { e.printStackTrace(); return; }

            try { stressval = Double.toString((Double) entry.get("stressval")); }
            catch (JSONException e) { stressval = ""; }
            catch (ClassCastException e) { stressval = ""; }
            try { photo = (String) entry.get("photo"); }
            catch (JSONException e) { photo = null; }
            catch (ClassCastException e) { photo = null; }
            try { category = (String) entry.get("category"); }
            catch (JSONException e) { category = ""; }
            catch (ClassCastException e) { category = ""; }
            try { subcategory = (String) entry.get("subcategory"); }
            catch (JSONException e) { subcategory = ""; }
            catch (ClassCastException e) { subcategory = ""; }
            try { comments = (String) entry.get("comments"); }
            catch (JSONException e) { comments = ""; }
            catch (ClassCastException e) { comments = ""; }
        }

        Log.d("POPUP", "about to set values from appspot");

        WebView wv = (WebView) findViewById (R.id.image);
        wv.getSettings().setJavaScriptEnabled(false);
        wv.loadUrl(photo);
        Log.d("POPUP", "loaded url: " + photo);

        ((TextView) findViewById (R.id.item_0)).setText(stressval);
        ((TextView) findViewById (R.id.item_1)).setText(category);
        ((TextView) findViewById (R.id.item_2)).setText(subcategory);
        ((TextView) findViewById (R.id.item_3)).setText(comments);
    }

    private String getUrlData(String url) {
        String websiteData = null;
        try {
            DefaultHttpClient client = new DefaultHttpClient();
            URI uri = new URI(url);
            HttpGet method = new HttpGet(uri);
            HttpResponse res = client.execute(method);
            InputStream data = res.getEntity().getContent();
            websiteData = generateString(data);
        } catch (ClientProtocolException e) { e.printStackTrace(); }
        catch (IOException e) { e.printStackTrace(); }
        catch (URISyntaxException e) { e.printStackTrace(); }
        return websiteData;
    }

    private String generateString(InputStream stream) {
        InputStreamReader reader = new InputStreamReader(stream);
        BufferedReader buffer = new BufferedReader(reader);
        StringBuilder sb = new StringBuilder();

        try {
            String cur;
            while ((cur = buffer.readLine()) != null) {
                sb.append(cur + "\n");
            }
        } catch (IOException e) { e.printStackTrace(); }

        try { stream.close(); } catch (IOException e) { e.printStackTrace(); }
        return sb.toString();
    }

}
