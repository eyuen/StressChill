package edu.ucla.cens.stresschillmap;

import java.util.ArrayList;

import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.database.SQLException;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.util.Log;

public class survey_db {
	public static final String KEY_Q_INT = "q_int";
    public static final String KEY_Q_CAT = "q_cat";
    public static final String KEY_Q_SUB = "q_sub";
    public static final String KEY_Q_COM = "q_com";
	public static final String KEY_LONGITUDE = "longitude";
	public static final String KEY_LATITUDE = "latitude";
	public static final String KEY_TIME = "time";
	public static final String KEY_PHOTO_FILENAME = "photo_filename";
    public static final String KEY_VERSION = "version";
	public static final String KEY_ROWID = "_id";
    public static final String KEY_ACCESS_TOKEN = "access_token";
    public static final String KEY_TOKEN_SECRET = "token_secret";
    public static final String KEY_REQUEST_TOKEN = "request_token";
	private static boolean databaseOpen = false;
	private static Object dbLock = new Object();
	public static final String TAG = "survey_db";
	private DatabaseHelper dbHelper;
	private SQLiteDatabase db;
	
	private Context mCtx = null;
	
	private static final String DATABASE_NAME = "survey_db";
	private static final String DATABASE_TABLE = "survey_table";
	private static final int DATABASE_VERSION = 7;
	
	private static final String DATABASE_CREATE = "create table survey_table (_id integer primary key autoincrement, "
        + "q_int text not null,"
        + "q_cat text not null,"
        + "q_sub text not null,"
        + "q_com text not null,"
		+ "longitude text not null,"
		+ "latitude text not null,"
		+ "time text not null,"
        + "version text not null,"
        + "photo_filename text not null,"
        + "access_token text not null,"
        + "token_secret text not null,"
        + "request_token text not null"
		+ ");";
	
    public class survey_db_row extends Object {
    	public long row_id;
        public String q_int;
        public String q_cat;
        public String q_sub;
        public String q_com;
    	public String longitude;
    	public String latitude;
    	public String time;
        public String version;
    	public String photo_filename;
        public String access_token;
        public String token_secret;
        public String request_token;
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

	public long createEntry(String q_int, String q_cat, String q_sub,
                            String q_com, String longitude, String latitude,
                            String time, String version, String photo_filename)
	{
		ContentValues vals = new ContentValues();
        vals.put(KEY_Q_INT, q_int);
        vals.put(KEY_Q_CAT, q_cat);
        vals.put(KEY_Q_SUB, q_sub);
        vals.put(KEY_Q_COM, q_com);
		vals.put(KEY_LONGITUDE, longitude);
		vals.put(KEY_LATITUDE, latitude);
		vals.put(KEY_TIME, time);
        vals.put(KEY_VERSION, version);
		vals.put(KEY_PHOTO_FILENAME, photo_filename);
        vals.put(KEY_ACCESS_TOKEN, authenticate.tokens.access_token);
        vals.put(KEY_TOKEN_SECRET, authenticate.tokens.token_secret);
        vals.put(KEY_REQUEST_TOKEN, authenticate.tokens.request_token);
		
		long rowid = db.insert(DATABASE_TABLE, null, vals);
		
		//to notify people who want to know if there are surveys left to upload
		mCtx.sendBroadcast(new Intent(constants.INTENT_ACTION_SURVEYS_CHANGED));
		
		return rowid;
	}
	
	public boolean deleteEntry(long rowId)
	{
		int count = 0;
		count = db.delete(DATABASE_TABLE, KEY_ROWID+"="+rowId, null);
		
		//to notify people who want to know if there are surveys left to upload
		mCtx.sendBroadcast(new Intent(constants.INTENT_ACTION_SURVEYS_CHANGED));

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

        sr.row_id =         c.getLong(0);
        sr.q_int =          c.getString(1);
        sr.q_cat =          c.getString(2);
        sr.q_sub =          c.getString(3);
        sr.q_com =          c.getString(4);
        sr.longitude =      c.getString(5);
        sr.latitude =       c.getString(6);
        sr.time =           c.getString(7);
        sr.version =        c.getString(8);
        sr.photo_filename = c.getString(9);
        sr.access_token =   c.getString(10);
        sr.token_secret =   c.getString(11);
        sr.request_token =  c.getString(12);

        return sr;
    }

	public ArrayList <survey_db_row>  fetchAllEntries()
    {
		ArrayList<survey_db_row> ret = new ArrayList<survey_db_row>();
		
		try
		{
			Cursor c = db.query(DATABASE_TABLE, new String[] {KEY_ROWID,
                KEY_Q_INT, KEY_Q_CAT, KEY_Q_SUB, KEY_Q_COM, KEY_LONGITUDE, KEY_LATITUDE,
                KEY_TIME, KEY_VERSION, KEY_PHOTO_FILENAME, KEY_ACCESS_TOKEN,
                KEY_TOKEN_SECRET, KEY_REQUEST_TOKEN}, null, null, null,
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
                KEY_Q_INT, KEY_Q_CAT, KEY_Q_SUB, KEY_Q_COM, KEY_LONGITUDE, KEY_LATITUDE,
                KEY_TIME, KEY_VERSION, KEY_PHOTO_FILENAME, KEY_ACCESS_TOKEN,
                KEY_TOKEN_SECRET, KEY_REQUEST_TOKEN};
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
            KEY_Q_INT, KEY_Q_CAT, KEY_Q_SUB, KEY_Q_COM, KEY_LONGITUDE, KEY_LATITUDE, KEY_TIME,
            KEY_VERSION, KEY_PHOTO_FILENAME, KEY_ACCESS_TOKEN,
            KEY_TOKEN_SECRET, KEY_REQUEST_TOKEN}, KEY_ROWID+"="+rowId, null, null,
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
            sr.q_int = sr.q_cat = sr.q_sub = sr.q_com =
            sr.longitude = sr.latitude = sr.time =
            sr.photo_filename = sr.access_token = sr.token_secret =
            sr.request_token = null;
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
        
		//to notify people who want to know if there are surveys left to upload
		mCtx.sendBroadcast(new Intent(constants.INTENT_ACTION_SURVEYS_CHANGED));
        
        return ret;
    }
    
    public Cursor gpsless_entries() {
    	return db.query(DATABASE_TABLE, new String[] {KEY_ROWID, KEY_LONGITUDE, KEY_LATITUDE}, KEY_LONGITUDE + "=\"\"" + " AND " + KEY_LATITUDE + "=\"\"", null, null, null, null);
    }
    
    public Cursor all_entries() {
    	return db.query(DATABASE_TABLE, new String[] {KEY_ROWID, KEY_LONGITUDE, KEY_LATITUDE}, null, null, null, null, null);
    }
    
    public boolean has_gpsless_entries() {
    	this.open();
    	Cursor cursor = gpsless_entries();
    	int count = cursor.getCount();
    	cursor.close();
    	this.close();
    	return count > 0;
    }

	public boolean has_entries() {
    	this.open();
    	Cursor cursor = all_entries();
    	int count = cursor.getCount();
    	cursor.close();
    	this.close();
    	return count > 0;
    }
}
