package edu.ucla.cens.stresschillmap;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.IntentFilter;
import android.database.Cursor;
import android.location.LocationManager;
import android.os.Bundle;
import android.util.Log;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;

public class home extends Activity {
    final public static String TAG = "Home Activity";
    private Context ctx;
	private survey_db sdb;
	
    @Override
    protected void onCreate(Bundle b) {
        super.onCreate (b);
        setContentView (R.layout.home);

        ctx = home.this;

        LocationManager lm = (LocationManager) getSystemService (
            Context.LOCATION_SERVICE);
        if (!lm.isProviderEnabled (LocationManager.GPS_PROVIDER)) {
            Log.d(TAG, "no gps was enabled, so enabling the gps now");
            alert_no_gps ();
        }
        lm = null;

        ((Button) findViewById (R.id.start_survey)).setOnClickListener (survey_button_listener);
        ((Button) findViewById (R.id.start_map)).setOnClickListener (map_button_listener);
        
        sdb = new survey_db(this);
        
        set_count();
        
		registerReceiver(mSurveysChangedReciever, new IntentFilter(constants.INTENT_ACTION_SURVEYS_CHANGED));
    }
    
	private final BroadcastReceiver mSurveysChangedReciever = new BroadcastReceiver() {
		@Override
		public void onReceive(Context context, Intent intent) {
	        set_count();
		}
	};
	
	public void set_count() {
        sdb.open();
        Cursor gpsless_entries = sdb.gpsless_entries();
        Cursor all_entries = sdb.all_entries();
        
        TextView num = ((TextView) home.this.findViewById (R.id.num_surveys));
        num.setText("There are "+gpsless_entries.getCount()+" surveys waiting for a gps lock \n There are "+all_entries.getCount()+" surveys waiting to upload");
        
        gpsless_entries.close();
        all_entries.close();
        sdb.close();
	}
	
	@Override
	public void onDestroy() {
		super.onDestroy();

		unregisterReceiver(mSurveysChangedReciever);
	}
	
    private void alert_no_gps() {
        final AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setMessage("Yout GPS seems to be disabled, You need GPS to run this application. do you want to enable it?")
               .setCancelable(false)
               .setPositiveButton("Yes", new DialogInterface.OnClickListener() {
                    public void onClick(final DialogInterface dialog, final int id) {
                        home.this.startActivityForResult(new Intent(android.provider.Settings.ACTION_LOCATION_SOURCE_SETTINGS), 3);
                    }
                })
               .setNegativeButton("No", new DialogInterface.OnClickListener() {
                    public void onClick(final DialogInterface dialog, final int id) {
                        home.this.finish();
                    }
                });
        final AlertDialog alert = builder.create();
        alert.show();
    }

    @Override
	protected void onActivityResult (int requestCode, int resultCode, Intent data) {
    }

    @Override
    public boolean onCreateOptionsMenu (Menu m) {
        super.onCreateOptionsMenu (m);

        m.add (Menu.NONE, 0, Menu.NONE, "About").setIcon (android.R.drawable.ic_menu_info_details);
        m.add (Menu.NONE, 1, Menu.NONE, "Instructions").setIcon (android.R.drawable.ic_menu_help);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected (MenuItem index) {
        Intent i;
        switch (index.getItemId()) {
            case 0:
                i = new Intent (ctx, about.class);
                break;
            case 1:
                i = new Intent (ctx, instructions.class);
                break;
            default:
                return false;
        }
        ctx.startActivity (i);
        return true;
    }

    View.OnClickListener survey_button_listener = new View.OnClickListener () {
        public void onClick (View v) {
            home.this.startActivity (new Intent (home.this, survey.class));
        }
    };

    View.OnClickListener map_button_listener = new View.OnClickListener () {
        public void onClick (View v) {
            home.this.startActivity (new Intent (home.this, map.class));
        }
    };
}
