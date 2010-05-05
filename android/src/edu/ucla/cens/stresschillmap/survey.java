package edu.ucla.cens.stresschillmap;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Date;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Bitmap.CompressFormat;
import android.os.Bundle;
import android.util.Log;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.view.View.OnClickListener;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.SeekBar;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;
import edu.ucla.cens.stresschillmap.survey_db.survey_db_row;

public class survey extends Activity
{
    private static final int ACTIVITY_CAPTURE_PHOTO = 0;
    private final String PIC_DATA_PATH = "/sdcard/stbpics";
    
    private Context ctx;
    private final String TAG = "Survey";
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
    private final View[][] view_list = new View[8][2];
    private final Spinner[] spinner = new Spinner[8];
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

        view_list[0][0] = findViewById(R.id.question_00);
        view_list[0][1] = findViewById(R.id.spinner_00);
        view_list[1][0] = findViewById(R.id.question_01);
        view_list[1][1] = findViewById(R.id.spinner_01);
        view_list[2][0] = findViewById(R.id.question_02);
        view_list[2][1] = findViewById(R.id.spinner_02);
        view_list[3][0] = findViewById(R.id.question_03);
        view_list[3][1] = findViewById(R.id.spinner_03);
        view_list[4][0] = findViewById(R.id.question_04);
        view_list[4][1] = findViewById(R.id.spinner_04);
        view_list[5][0] = findViewById(R.id.question_05);
        view_list[5][1] = findViewById(R.id.spinner_05);
        view_list[6][0] = findViewById(R.id.question_06);
        view_list[6][1] = findViewById(R.id.spinner_06);
        view_list[7][0] = findViewById(R.id.question_07);
        view_list[7][1] = findViewById(R.id.spinner_07);

        int si = 0;
        spinner[si] = (Spinner) findViewById(R.id.spinner_00);
        ArrayAdapter adapter = ArrayAdapter.createFromResource(
            this, R.array.response_00, android.R.layout.simple_spinner_item);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner[si].setAdapter(adapter);
        spinner[si++].setOnItemSelectedListener(spin_listener_0);

        spinner[si] = (Spinner) findViewById(R.id.spinner_01);
        adapter = ArrayAdapter.createFromResource(
            this, R.array.response_01, android.R.layout.simple_spinner_item);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner[si++].setAdapter(adapter);

        spinner[si] = (Spinner) findViewById(R.id.spinner_02);
        adapter = ArrayAdapter.createFromResource(
            this, R.array.response_02, android.R.layout.simple_spinner_item);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner[si++].setAdapter(adapter);

        spinner[si] = (Spinner) findViewById(R.id.spinner_03);
        adapter = ArrayAdapter.createFromResource(
            this, R.array.response_03, android.R.layout.simple_spinner_item);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner[si++].setAdapter(adapter);

        spinner[si] = (Spinner) findViewById(R.id.spinner_04);
        adapter = ArrayAdapter.createFromResource(
            this, R.array.response_04, android.R.layout.simple_spinner_item);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner[si++].setAdapter(adapter);

        spinner[si] = (Spinner) findViewById(R.id.spinner_05);
        adapter = ArrayAdapter.createFromResource(
            this, R.array.response_05, android.R.layout.simple_spinner_item);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner[si++].setAdapter(adapter);

        spinner[si] = (Spinner) findViewById(R.id.spinner_06);
        adapter = ArrayAdapter.createFromResource(
            this, R.array.response_06, android.R.layout.simple_spinner_item);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner[si++].setAdapter(adapter);

        spinner[si] = (Spinner) findViewById(R.id.spinner_07);
        adapter = ArrayAdapter.createFromResource(
            this, R.array.response_07, android.R.layout.simple_spinner_item);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner[si++].setAdapter(adapter);

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
    public void onDestroy() {
    	super.onDestroy();
    	sdb.open();
        if (!sdb.has_gpsless_entries()) {
            stopService (new Intent(ctx, light_loc.class));
            preferences.edit().putBoolean ("light_loc", false).commit ();
        }
        sdb.close();
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
    @Override
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
            String q_sub = "0";
            String q_com = comment.getText().toString();

            /* figure out which category the user selected
             * there is likely a much more efficient/clean way to do this.
             * please do implement it if it comes to you */
            int main_index = spinner[0].getSelectedItemPosition();

            if (main_index < 1 || spinner.length <= main_index)
            {
                Toast
                .makeText (survey.this,
                           "You have not answered the main category question.",
                           Toast.LENGTH_LONG)
                .show();
                return;
            }

            TextView sub_view = (TextView) spinner[main_index].getSelectedView();
            if (null == sub_view
                || sub_view.getText().toString().equals("Select one..."))
            {
                Toast
                .makeText (survey.this,
                           "You have not answered the sub category question.",
                           Toast.LENGTH_LONG)
                .show();
                return;
            }

            q_cat = ((TextView) spinner[0].getSelectedView()).getText().toString();
            q_sub = sub_view.getText().toString();
            q_int = ((TextView)findViewById (R.id.stress_value)).getText().toString();

            String longitude = "";
            String latitude = "";
            String time = Long.toString(d.getTime());
            String photo_filename = filename;

            sdb.open();
            long row_id = sdb.createEntry(q_int, q_cat, q_sub, q_com, longitude, latitude,
                                          time, getString(R.string.version), photo_filename);
            sdb.close();

            sdb.open();
            survey_db_row sr = sdb.fetchEntry(row_id);
            sdb.close();

            Log.d("SUBMIT SURVEY", Long.toString(sr.row_id) + ", " +
                                   sr.q_int + ", " +
                                   sr.q_cat + ", " +
                                   sr.q_sub + ", " +
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
            
            // should start the service upload thread when there is actually a survey to upload
            startService(new Intent(ctx, survey_upload.class));
            Log.d(TAG, "started survey upload intent");

            // restart this view
            Toast.makeText(survey.this, "Survey successfully submitted!", Toast.LENGTH_LONG).show();
            ctx.startActivity (new Intent(ctx, home.class));
            //survey.this.finish();
        }
    };

    OnClickListener take_picture_listener = new OnClickListener() {
        public void onClick(View v) {
            Intent intent = new Intent("android.media.action.IMAGE_CAPTURE");
            startActivityForResult(intent, ACTIVITY_CAPTURE_PHOTO);
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

    private final Spinner.OnItemSelectedListener spin_listener_0 = new Spinner.OnItemSelectedListener() {
        public void onItemSelected(AdapterView parent, View v, int position, long id) {
            for (int i = 0; i < 2; i++) {
                view_list[position][i].setVisibility (View.VISIBLE);
            }
            for (int i = 1; i < view_list.length; i++) {
                if (i == position) continue;
                for (int j = 0; j < 2; j++) {
                    view_list[i][j].setVisibility (View.GONE);
                }
            }
        }
        public void onNothingSelected(AdapterView parent) { }
    };

    @Override
	protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        switch(requestCode) {
        case ACTIVITY_CAPTURE_PHOTO:
            if (RESULT_CANCELED != resultCode) {
                Bitmap image = (Bitmap) data.getExtras().get("data");

                Date date = new Date();
                long time = date.getTime();
                filename = PIC_DATA_PATH + "/"
                        + time + ".jpg";

                try {
                    File ld = new File(PIC_DATA_PATH);
                    if (ld.exists()) {
                        if (!ld.isDirectory()) {
                            // TODO Handle exception
                            break;
                        }
                    } else {
                        ld.mkdir();
                    }

                    OutputStream os = new FileOutputStream(filename);
                    image.compress(CompressFormat.JPEG, 100, os);
                    os.close();
                    
                    image_preview.setImageBitmap(image);
                } catch (FileNotFoundException e) {
                    e.printStackTrace();
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
            break;
        }
    }
}
