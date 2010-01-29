package edu.ucla.cens.stresschillmap;

import java.util.ArrayList;


import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.SQLException;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.util.Log;

public class survey_db {
	public static final String KEY_Q_INT = "q_int";
    public static final String KEY_Q_CAT = "q_cat";
	public static final String KEY_LONGITUDE = "longitude";
	public static final String KEY_LATITUDE = "latitude";
	public static final String KEY_TIME = "time";
	public static final String KEY_PHOTO_FILENAME = "photo_filename";
    public static final String KEY_VERSION = "version";
	public static final String KEY_ROWID = "_id";
	private static boolean databaseOpen = false;
	private static Object dbLock = new Object();
	public static final String TAG = "survey_db";
	private DatabaseHelper dbHelper;
	private SQLiteDatabase db;
	
	private Context mCtx = null;
	
	private static final String DATABASE_NAME = "survey_db";
	private static final String DATABASE_TABLE = "survey_table";
	private static final int DATABASE_VERSION = 2;
	
	private static final String DATABASE_CREATE = "create table survey_table (_id integer primary key autoincrement, "
        + "q_int text not null,"
        + "q_cat text not null,"
		+ "longitude text not null,"
		+ "latitude text not null,"
		+ "time text not null,"
        + "version text not null,"
		+ "photo_filename text not null"
		+ ");";
	
    public class survey_db_row extends Object {
    	public long row_id;
        public String q_int;
        public String q_cat;
    	public String longitude;
    	public String latitude;
    	public String time;
        public String version;
    	public String photo_filename;
    }
	
	private static class DatabaseHelper extends SQLiteOpenHelper
	{
		DatabaseHelper(Context ctx)
		{
			super(ctx, DATABASE_NAME, null, DATABASE_VERSION);
		}

		@Override
		public void onCreate(SQLiteDatabase db) {
			db.execSQL(DATABASE_CREATE);
		}

		@Override
		public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
			db.execSQL("DROP TABLE IF EXISTS " + DATABASE_TABLE);
			onCreate(db);
		}
	}
	
	public survey_db(Context ctx)
	{
		mCtx = ctx;
	}
	
	public survey_db open() throws SQLException
    {
		synchronized(dbLock)
		{
			while (databaseOpen)
			{
				try
				{
					dbLock.wait();
				}
				catch (InterruptedException e){}
			}
			databaseOpen = true;
			dbHelper = new DatabaseHelper(mCtx);
			db = dbHelper.getWritableDatabase();

			return this;
		}
	}
	
	public void close()
	{
		synchronized(dbLock)
		{
			dbHelper.close();
			databaseOpen = false;
			dbLock.notify();
		}
	}

	public long createEntry(String q_int, String q_cat,
                            String longitude, String latitude, String time,
                            String version, String photo_filename)
	{
		ContentValues vals = new ContentValues();
        vals.put(KEY_Q_INT, q_int);
        vals.put(KEY_Q_CAT, q_cat);
		vals.put(KEY_LONGITUDE, longitude);
		vals.put(KEY_LATITUDE, latitude);
		vals.put(KEY_TIME, time);
        vals.put(KEY_VERSION, version);
		vals.put(KEY_PHOTO_FILENAME, photo_filename);
		
		long rowid = db.insert(DATABASE_TABLE, null, vals);
		return rowid;
	}
	
	public boolean deleteEntry(long rowId)
	{
		int count = 0;
		count = db.delete(DATABASE_TABLE, KEY_ROWID+"="+rowId, null);
		
        if(count > 0) {
            return true;
        }
        return false;
	}

    public void refresh_db()
    {
        db.execSQL("DROP TABLE IF EXISTS " + DATABASE_TABLE);
        db.execSQL(DATABASE_CREATE);
    }

    private survey_db_row populate_row (Cursor c) {
        survey_db_row sr = new survey_db_row();

        sr.row_id = c.getLong(0);
        sr.q_int = c.getString(1);
        sr.q_cat = c.getString(2);
        sr.longitude = c.getString(3);
        sr.latitude = c.getString(4);
        sr.time = c.getString(5);
        sr.version = c.getString(6);
        sr.photo_filename = c.getString(7);

        return sr;
    }

	public ArrayList <survey_db_row>  fetchAllEntries()
    {
		ArrayList<survey_db_row> ret = new ArrayList<survey_db_row>();
		
		try
		{
			Cursor c = db.query(DATABASE_TABLE, new String[] {KEY_ROWID,
                KEY_Q_INT, KEY_Q_CAT, KEY_LONGITUDE, KEY_LATITUDE,
                KEY_TIME, KEY_VERSION, KEY_PHOTO_FILENAME}, null, null, null,
                null, null);
			int numRows = c.getCount();
			
			c.moveToFirst();
			
			for (int i =0; i < numRows; ++i)
			{
				survey_db_row sr = populate_row (c); 
				ret.add(sr);
				c.moveToNext();
			}
			c.close();
		}
		catch (Exception e){
			Log.e(TAG, e.getMessage());
		}
		return ret;
	}

    public ArrayList <survey_db_row>  fetch_all_completed_entries()
    {
        ArrayList<survey_db_row> ret = new ArrayList<survey_db_row>();

        try
        {
            String[] columns = new String[] {KEY_ROWID,
                KEY_Q_INT, KEY_Q_CAT, KEY_LONGITUDE, KEY_LATITUDE,
                KEY_TIME, KEY_VERSION, KEY_PHOTO_FILENAME};
            String selection = KEY_LONGITUDE + "<>\"\"" + " AND " +
                               KEY_LATITUDE + "<>\"\"";

            Cursor c = db.query(DATABASE_TABLE, columns, selection, null, null,
                                null, null);
            int numRows = c.getCount();

            c.moveToFirst();

            for (int i =0; i < numRows; ++i)
            {
                survey_db_row sr = populate_row (c);
                ret.add(sr);
                c.moveToNext();
            }
            c.close();
        }
        catch (Exception e){
            Log.e(TAG, e.getMessage());
        }
        return ret;
    }

	public survey_db_row fetchEntry(long rowId) throws SQLException
	{
        Cursor c = db.query(DATABASE_TABLE, new String[] {KEY_ROWID,
            KEY_Q_INT, KEY_Q_CAT, KEY_LONGITUDE, KEY_LATITUDE, KEY_TIME,
            KEY_VERSION, KEY_PHOTO_FILENAME}, KEY_ROWID+"="+rowId, null, null,
            null, null);
		survey_db_row sr;

		if (c != null) {
			c.moveToFirst();
            sr = populate_row (c);
		}
		else
		{
            sr = new survey_db_row();
            sr.row_id = -1;
            sr.q_int = sr.q_cat =
            sr.longitude = sr.latitude = sr.time =
            sr.photo_filename = null;
		}
		c.close();
		return sr;
	}

    public int update_gpsless_entries (String lon, String lat) {
        ContentValues values = new ContentValues();
        values.put (KEY_LONGITUDE, lon);
        values.put (KEY_LATITUDE, lat);

        String where_clause = KEY_LONGITUDE + "=\"\"" + " AND " + KEY_LATITUDE + "=\"\"";

        int ret = db.update (DATABASE_TABLE, values, where_clause, null);
        return ret;
    }
}
