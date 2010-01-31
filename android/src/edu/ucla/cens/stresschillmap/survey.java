package edu.ucla.cens.stresschillmap;

import android.app.Activity;
import android.os.Bundle;
import android.util.Log;

import android.widget.TextView;

import android.content.Context;
import android.content.Intent;
import android.content.DialogInterface;
import android.content.SharedPreferences;

import android.location.LocationManager;
import android.location.Location;
import android.location.Criteria;

import android.view.View;
import android.view.View.OnClickListener;
import android.view.Menu;
import android.view.MenuItem;
import android.view.LayoutInflater;

import android.widget.ImageView;
import android.widget.Button;
import android.widget.ImageButton;
import android.widget.EditText;
import android.widget.Toast;
import android.widget.CheckBox;
import android.widget.Spinner;
import android.widget.ArrayAdapter;
import android.widget.AdapterView;
import android.app.AlertDialog;
import android.app.Dialog;
       

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;

import java.io.File;
import java.util.Iterator;
import java.util.List;
import java.util.ArrayList;
import java.util.Date;

import edu.ucla.cens.stresschillmap.light_loc;
import edu.ucla.cens.stresschillmap.survey_db;
import edu.ucla.cens.stresschillmap.survey_db.survey_db_row;

import android.widget.SeekBar;

public class survey extends Activity
{
    private Context ctx;
    private String TAG = "Survey";
    private Button take_picture;
    private Button submit_button;
    //private Button clear_history;
    private ImageView image_preview;
    private String filename = "";
    private light_loc ll;
    private survey_db sdb;
    private SharedPreferences preferences;
    private TextView stress_value;
    private SeekBar seek_bar;
    private View[][] view_list = new View[3][2];
    private Spinner spinner_0;
    private Spinner spinner_1;
    private Spinner spinner_2;
    private TextView comment;

    /** Called when the activity is first created. */
    @Override
    public void onCreate(Bundle savedInstanceState)
    {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.survey);

        ctx = survey.this;

        comment = (EditText) findViewById(R.id.comment);
        stress_value = (TextView) findViewById(R.id.stress_value);
        seek_bar = (SeekBar) findViewById(R.id.chillstress_seekbar);

        seek_bar.setOnSeekBarChangeListener (seek_bar_updater);

        preferences = getSharedPreferences(getString(R.string.preferences), Activity.MODE_PRIVATE);
        // allow users to collect data even if they are not yet authenticated
        // let the survey_upload service make sure they are auth'd before
        // uploading... (lets users collect data without internet conn)
        //if (!preferences.getBoolean("authenticated", false)) {
        //    Log.d(TAG, "exiting (not authenticated)");
        //    survey.this.finish();
        //    return;
        //}

        sdb = new survey_db(this);

        /* start location service */
        startService (new Intent(ctx, light_loc.class));
        preferences.edit().putBoolean ("light_loc", true).commit ();

        Log.d(TAG, "gps listener and db are started");

        view_list[0][0] = findViewById(R.id.item_row_0_0);
        view_list[0][1] = findViewById(R.id.item_row_0_1);
        view_list[1][0] = findViewById(R.id.item_row_1_0);
        view_list[1][1] = findViewById(R.id.item_row_1_1);
        view_list[2][0] = findViewById(R.id.item_row_2_0);
        view_list[2][1] = findViewById(R.id.item_row_2_1);

        spinner_0 = (Spinner) findViewById(R.id.spinner_00);
        ArrayAdapter adapter = ArrayAdapter.createFromResource(
            this, R.array.response_00, android.R.layout.simple_spinner_item);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner_0.setAdapter(adapter);
        spinner_0.setOnItemSelectedListener(spin_listener_0);

        spinner_1 = (Spinner) findViewById(R.id.spinner_01);
        adapter = ArrayAdapter.createFromResource(
            this, R.array.response_01, android.R.layout.simple_spinner_item);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner_1.setAdapter(adapter);

        spinner_2 = (Spinner) findViewById(R.id.spinner_02);
        adapter = ArrayAdapter.createFromResource(
            this, R.array.response_02, android.R.layout.simple_spinner_item);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner_2.setAdapter(adapter);

        // add buttons
        submit_button = (Button) findViewById(R.id.upload_button);
        take_picture = (Button) findViewById(R.id.image_button);
        
        // add image preview
        image_preview = (ImageView) findViewById(R.id.image_preview);

        // add button listeners
        submit_button.setOnClickListener(submit_button_listener);
        take_picture.setOnClickListener(take_picture_listener);

        // restore previous state (if available)
        if (savedInstanceState != null && savedInstanceState.getBoolean("started")) {
            filename = savedInstanceState.getString("filename");
            if ((null != filename) && (filename.toString() != "")) {
                Bitmap bm = BitmapFactory.decodeFile(filename);
                if (bm != null) {
                    image_preview.setImageBitmap(bm);
                }
            }
        }

        return;
    }

    @Override
    public boolean onCreateOptionsMenu (Menu m) {
        super.onCreateOptionsMenu (m);

        m.add (Menu.NONE, 0, Menu.NONE, "Home").setIcon (android.R.drawable.ic_menu_revert);
        m.add (Menu.NONE, 1, Menu.NONE, "Map").setIcon (android.R.drawable.ic_menu_mapmode);
        m.add (Menu.NONE, 2, Menu.NONE, "About").setIcon (android.R.drawable.ic_menu_info_details);
        m.add (Menu.NONE, 3, Menu.NONE, "Instructions").setIcon (android.R.drawable.ic_menu_help);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected (MenuItem index) {
        Intent i;
        switch (index.getItemId()) {
            case 0:
                i = new Intent (ctx, home.class);
                break;
            case 1:
                i = new Intent (ctx, map.class);
                break;
            case 2:
                i = new Intent (ctx, about.class);
                break;
            case 3:
                i = new Intent (ctx, instructions.class);
                break;
            default:
                return false;
        }
        ctx.startActivity (i);
        //this.finish();
        return true;
    }

    private void alert_no_gps() {
        final AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setMessage("Yout GPS seems to be disabled, You need GPS to run this application. do you want to enable it?")
               .setCancelable(false)
               .setPositiveButton("Yes", new DialogInterface.OnClickListener() {
                    public void onClick(final DialogInterface dialog, final int id) {
                        survey.this.startActivityForResult(new Intent(android.provider.Settings.ACTION_LOCATION_SOURCE_SETTINGS), 3);
                    }
                })
               .setNegativeButton("No", new DialogInterface.OnClickListener() {
                    public void onClick(final DialogInterface dialog, final int id) {
                        survey.this.finish();
                    }
                });
        final AlertDialog alert = builder.create();
        alert.show();
    }

    // if this activity gets killed for any reason, save the status of the
    // check boxes so that they are filled in the next time it gets run
    public void onSaveInstanceState(Bundle savedInstanceState) {
        savedInstanceState.putBoolean("started", true);
        savedInstanceState.putString("filename", filename);

        super.onSaveInstanceState(savedInstanceState);
    }

    SeekBar.OnSeekBarChangeListener seek_bar_updater = new SeekBar.OnSeekBarChangeListener() {
        public void onStartTrackingTouch(SeekBar seekBar) {
            return;
        }
        public void onProgressChanged (SeekBar sb, int progress, boolean fromUser) {
            double adj_val = (progress - 50) / 5.0;

            stress_value.setText(Double.toString(adj_val));
        }
        public void onStopTrackingTouch(SeekBar seekBar) {
            return;
        }
    };

    OnClickListener submit_button_listener = new OnClickListener() {
        public void onClick(View v) {
            Date d = new Date();

            String q_int = "0";
            String q_cat = "0";
            String q_com = comment.getText().toString();

            /* figure out which category the user selected
             * there is likely a much more efficient/clean way to do this.
             * please do implement it if it comes to you */
            TextView v0 = (TextView) spinner_0.getSelectedView();
            TextView v1 = (TextView) spinner_1.getSelectedView();
            TextView v2 = (TextView) spinner_2.getSelectedView();

            if (null == v0
                || v0.getText().toString().equals("Select one..."))
            {
                Toast
                .makeText (survey.this,
                           "You have not answered the category question.",
                           Toast.LENGTH_LONG)
                .show();
                return;
            }

            if (v0.getText().toString().equals(getString(R.string.radio_group_1_option_1))) {
                if (null == v1
                    || v1.getText().toString().equals("Select one..."))
                {
                    Toast
                    .makeText (survey.this,
                               "You have not answered the sub category question.",
                               Toast.LENGTH_LONG)
                    .show();
                    return;
                }
                q_cat = v1.getText().toString();
            } else if (v0.getText().toString().equals(getString(R.string.radio_group_1_option_6))) {
                if (null == v2
                    || v2.getText().toString().equals("Select one..."))
                {
                    Toast
                    .makeText (survey.this,
                               "You have not answered the sub category question.",
                               Toast.LENGTH_LONG)
                    .show();
                    return;
                }
                q_cat = v2.getText().toString();
            } else {
                q_cat = v0.getText().toString();
            }

            q_int = ((TextView)findViewById (R.id.stress_value)).getText().toString();

            String longitude = "";
            String latitude = "";
            String time = Long.toString(d.getTime());
            String photo_filename = filename;

            sdb.open();
            long row_id = sdb.createEntry(q_int, q_cat, q_com, longitude, latitude,
                                          time, getString(R.string.version), photo_filename);
            sdb.close();

            sdb.open();
            survey_db_row sr = sdb.fetchEntry(row_id);
            sdb.close();

            Log.d("SUBMIT SURVEY", Long.toString(sr.row_id) + ", " +
                                   sr.q_int + ", " +
                                   sr.q_cat + ", " +
                                   sr.longitude + ", " +
                                   sr.latitude + ", " +
                                   sr.time + ", " +
                                   sr.version + ", " +
                                   sr.photo_filename + ".");

            /* start location service */
            if (!preferences.getBoolean("light_loc", false)) {
                startService (new Intent(ctx, light_loc.class));
                preferences.edit().putBoolean ("light_loc", true).commit ();
            }

            // restart this view
            Toast.makeText(survey.this, "Survey successfully submitted!", Toast.LENGTH_LONG).show();
            ctx.startActivity (new Intent(ctx, home.class));
            //survey.this.finish();
        }
    };

    OnClickListener take_picture_listener = new OnClickListener() {
        public void onClick(View v) {
            Intent photo_intent = new Intent(survey.this, photo.class);
            startActivityForResult(photo_intent, 0);
        }
    };

    OnClickListener clear_history_listener = new OnClickListener() {
        public void onClick(View v) {
            sdb.open();
            ArrayList<survey_db_row> sr_list = sdb.fetchAllEntries();
            sdb.close();

            for (int i = 0; i < sr_list.size(); i++) {
                survey_db_row sr = sr_list.get(i);
                File file = null;
                if ((sr.photo_filename != null) && (sr.photo_filename.toString() != "")) {
                    file = new File(sr.photo_filename.toString());
                }
                if(file != null) {
                    file.delete();
                }
                sdb.open();
                sdb.deleteEntry(sr.row_id);
                sdb.close();
            }

/*
            sdb.open();
            sdb.refresh_db();
            sdb.close();
            */
        }
    };

    private Spinner.OnItemSelectedListener spin_listener_0 = new Spinner.OnItemSelectedListener() {
        public void onItemSelected(AdapterView parent, View v, int position, long id) {
            for (int i = 0; i < 2; i++) {
                view_list[1][i].setVisibility (1 == position ? View.VISIBLE : View.GONE);
                view_list[2][i].setVisibility (6 == position ? View.VISIBLE : View.GONE);
            }
        }
        public void onNothingSelected(AdapterView parent) { }
    };

    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (RESULT_CANCELED != resultCode) {
            filename = data.getAction().toString();
            if ((null != filename) && (filename.toString() != "")) {
                Bitmap bm = BitmapFactory.decodeFile(filename);
                if (bm != null) {
                    image_preview.setImageBitmap(bm);
                }
            }
        }
    }
}
