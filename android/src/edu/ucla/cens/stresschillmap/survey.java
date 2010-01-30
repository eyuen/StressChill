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

import android.widget.ImageView;
import android.widget.Button;
import android.widget.ImageButton;
import android.widget.RadioButton;
import android.widget.EditText;
import android.widget.Toast;
import android.widget.CheckBox;
import android.widget.RadioGroup;
import android.app.AlertDialog;
       

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
    private ImageButton take_picture;
    private Button submit_button;
    //private Button clear_history;
    private ImageView image_preview;
    private String filename = "";
    private light_loc ll;
    private survey_db sdb;
    private SharedPreferences preferences;
    private TextView stress_value;
    private SeekBar seek_bar;
    private RadioGroup radio_group_1;
    private RadioGroup radio_group_2;
    private RadioGroup radio_group_3;
    private ArrayList<ArrayList<RadioButton>> radio_button_list = new ArrayList<ArrayList<RadioButton>>();

    /** Called when the activity is first created. */
    @Override
    public void onCreate(Bundle savedInstanceState)
    {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.survey);

        ctx = survey.this;

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

        LocationManager lm = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
        if (!lm.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                        Log.d(TAG, "no gps was enabled, so enabling the gps now");
            alert_no_gps();
        }

        ll = new light_loc (this, lm);
        sdb = new survey_db(this);

        Log.d(TAG, "gps listener and db are started");

        // add radio groups
        radio_group_1 = (RadioGroup) findViewById (R.id.radio_group_1);
        radio_group_2 = (RadioGroup) findViewById (R.id.radio_group_2);
        radio_group_3 = (RadioGroup) findViewById (R.id.radio_group_3);

        // add radio button ids
        ArrayList<RadioButton> lcb;
        lcb = new ArrayList<RadioButton>();
        lcb.add ((RadioButton)findViewById(R.id.radio_group_1_option_1));
        lcb.add ((RadioButton)findViewById(R.id.radio_group_1_option_2));
        lcb.add ((RadioButton)findViewById(R.id.radio_group_1_option_3));
        lcb.add ((RadioButton)findViewById(R.id.radio_group_1_option_4));
        lcb.add ((RadioButton)findViewById(R.id.radio_group_1_option_5));
        lcb.add ((RadioButton)findViewById(R.id.radio_group_1_option_6));
        radio_button_list.add (lcb);
        Log.d (TAG, "added radio_group_1 options");

        lcb = new ArrayList<RadioButton>();
        lcb.add ((RadioButton)findViewById(R.id.radio_group_2_option_1));
        lcb.add ((RadioButton)findViewById(R.id.radio_group_2_option_2));
        lcb.add ((RadioButton)findViewById(R.id.radio_group_2_option_3));
        lcb.add ((RadioButton)findViewById(R.id.radio_group_2_option_4));
        lcb.add ((RadioButton)findViewById(R.id.radio_group_2_option_5));
        radio_button_list.add (lcb);
        Log.d (TAG, "added radio_group_2 options");

        lcb = new ArrayList<RadioButton>();
        lcb.add ((RadioButton)findViewById(R.id.radio_group_3_option_1));
        lcb.add ((RadioButton)findViewById(R.id.radio_group_3_option_2));
        lcb.add ((RadioButton)findViewById(R.id.radio_group_3_option_3));
        radio_button_list.add (lcb);
        Log.d (TAG, "added radio_group_3 options");


        // add change listener to radio group 1
        radio_group_1.setOnCheckedChangeListener (radio_group_1_listener);

        // add submit button
        submit_button = (Button) findViewById(R.id.upload_button);

        // add picture button
        take_picture = (ImageButton) findViewById(R.id.image_button);
        image_preview = (ImageView) findViewById(R.id.image_preview);

        // add image thumbnail view
        image_preview = (ImageView) findViewById(R.id.image_button);

        // add submit button listener
        submit_button.setOnClickListener(submit_button_listener);

        // add take picture button listener
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

    /* XXX if uncommented location won't be able to be updated when other
    * views are active
    protected void onPause() {
        if (null != ll) {
            ll.my_delete();
            ll = null;
        }
        super.onPause();
    }
    protected void onResume() {
        super.onResume();
        if (null == ll) {
            ll = new light_loc(this, (LocationManager) getSystemService(Context.LOCATION_SERVICE));
        }
    }

    protected void onStop() {
        if (null != ll) {
            ll.my_delete();
            ll = null;
        }
        super.onStop();
    }
    */
    protected void onStart() {
        super.onStart();
        if (null == ll) {
            ll = new light_loc(this, (LocationManager) getSystemService(Context.LOCATION_SERVICE));
        }
    }

    protected void onDestroy() {
        if (null != ll) {
            ll.my_delete();
            ll = null;
        }
        super.onDestroy();
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

    RadioGroup.OnCheckedChangeListener radio_group_1_listener = new RadioGroup.OnCheckedChangeListener() {
        public void onCheckedChanged (RadioGroup group, int checkedId) {
            List<RadioButton> lcb = radio_button_list.get(0);
            int index = -1;

            for (int i = 0; i < lcb.size(); i++) {
                RadioButton rb = lcb.get(i);
                if (checkedId == rb.getId()) {
                    index = i;
                    break;
                }
            }

            if (-1 == index) {
                return;
            }

            radio_group_2.setVisibility (0 == index ? View.VISIBLE : View.GONE);
            radio_group_3.setVisibility (5 == index ? View.VISIBLE : View.GONE);
        }
    };

    private int get_checked_index (RadioGroup group, int group_index) {
        int id = group.getCheckedRadioButtonId();
        List<RadioButton> lcb = radio_button_list.get(group_index);
        int index = -1;

        for (int i = 0; i < lcb.size(); i++) {
            RadioButton rb = lcb.get (i);
            if (id == rb.getId()) {
                index = i;
                break;
            }
        }

        return index;
    }

    private String get_checked_string (int group_index, int radio_index) {
        List<RadioButton> lcb = radio_button_list.get(group_index);
        RadioButton rb = lcb.get (radio_index);
        return rb.getText().toString();
    }

    OnClickListener submit_button_listener = new OnClickListener() {
        public void onClick(View v) {
            Date d = new Date();

            String q_int = "0";
            String q_cat = "0";

            int group_1_ans = get_checked_index (radio_group_1, 0);
            int group_2_ans = get_checked_index (radio_group_2, 1);
            int group_3_ans = get_checked_index (radio_group_3, 2);

            if (0 == group_1_ans || 5 == group_1_ans) {
                if ((0 == group_1_ans && -1 == group_2_ans)
                    || (5 == group_1_ans && -1 == group_3_ans))
                {
                    Toast
                    .makeText (survey.this,
                               "You have not answered the sub category question.",
                               Toast.LENGTH_LONG)
                    .show();
                    return;
                }

                q_cat = get_checked_string (0 == group_1_ans ? 1 : 2,
                                            0 == group_1_ans ? group_2_ans : group_3_ans);
            } else {
                q_cat = get_checked_string (0, group_1_ans);
            }

            q_int = ((TextView)findViewById (R.id.stress_value)).getText().toString();

            String longitude = "";
            String latitude = "";
            String time = Long.toString(d.getTime());
            String photo_filename = filename;

            sdb.open();
            long row_id = sdb.createEntry(q_int, q_cat, longitude, latitude,
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
