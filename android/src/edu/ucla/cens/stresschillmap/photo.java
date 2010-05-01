package edu.ucla.cens.stresschillmap;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.util.Date;
import java.util.List;

import android.app.Activity;
import android.content.Intent;
import android.graphics.PixelFormat;
import android.hardware.Camera;
import android.os.Bundle;
import android.os.Build;
import android.util.Log;
import android.view.KeyEvent;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.widget.Toast;

public class photo extends Activity implements SurfaceHolder.Callback
{
    private static final String TAG = "Photo";
	private final String PIC_DATA_PATH = "/sdcard/stbpics"; //rcp-chillstressmap";XXX
	String fname;
    
    Camera mCamera;
    boolean mPreviewRunning = false;
    private boolean clicked = false;


    public void onCreate(Bundle savedInstanceState)
    {
        super.onCreate(savedInstanceState);
        
        Toast 
        .makeText(this, "Take photo by pressing camera button or center directional pad.  After you are done capturing photos, press back key.", Toast.LENGTH_LONG) 
        .show(); 

        Log.d(TAG, "onCreate");

        getWindow().setFormat(PixelFormat.TRANSLUCENT);

        setContentView(R.layout.photo);
        mSurfaceView = (SurfaceView)findViewById(R.id.surface);
        Log.d(TAG, "set layout");

        mSurfaceHolder = mSurfaceView.getHolder();
        mSurfaceHolder.addCallback(this);
        mSurfaceHolder.setType(SurfaceHolder.SURFACE_TYPE_PUSH_BUFFERS);
        Log.d(TAG, "set callbacks");
    }
    
    @Override
    protected void onRestoreInstanceState(Bundle savedInstanceState)
    {
        super.onRestoreInstanceState(savedInstanceState);
    }

    Camera.PictureCallback mPictureCallback = new Camera.PictureCallback() {
        public void onPictureTaken(byte[] data, Camera c) {
            Log.d(TAG, "PICTURE CALLBACK: data.length = " + data.length);
            
            Date now = new Date();
            long nowLong = now.getTime(); 
            fname = PIC_DATA_PATH+"/"+nowLong+".jpg";
            
            try {
            	
                File ld = new File(PIC_DATA_PATH);
                if (ld.exists()) {
                	if (!ld.isDirectory()){

                		// Should probably inform user ... hmm!
                		Log.d(TAG, "Failed to create pic directory");
                    	photo.this.finish();
                	}
                } else {
                	ld.mkdir();
                }
            	
                     
                Log.d(TAG, fname);         
                
				OutputStream os = new FileOutputStream(fname);
				os.write(data,0,data.length);
				os.close();
			} catch (FileNotFoundException e) {
				Log.d(TAG, "Could not write picture");
			} catch (IOException e) {
				Log.d(TAG, "Could not write picture");
			}
            
			//setResult is used to send result back to the Activity 
			//that started this one.
			setResult(RESULT_OK,(new Intent()).setAction(fname.toString()));
			finish();
			
            //mCamera.startPreview();
        }
    };

    public boolean onKeyDown(int keyCode, KeyEvent event)
    {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
        	photo.this.finish();
        	return false;
            //return super.onKeyDown(keyCode, event);
        }
 
        if (keyCode == KeyEvent.KEYCODE_CAMERA || keyCode == KeyEvent.KEYCODE_DPAD_CENTER) 
        {
        	if (!clicked){
        		//mCamera.takePicture(null, null, mPictureCallback);
        		clicked = true;
        		mCamera.autoFocus(mAutoFocusCallback);
        		return true;
        	}        	
        }

        return false;
    }
    
    Camera.AutoFocusCallback mAutoFocusCallback = new Camera.AutoFocusCallback (){

		public void onAutoFocus(boolean success, Camera camera) {
            mCamera.takePicture(null, null, mPictureCallback);
			
		}
    	
    };

    protected void onResume()
    {
        Log.d(TAG, "onResume");
        super.onResume();
    }

    protected void onSaveInstanceState(Bundle outState)
    {
        super.onSaveInstanceState(outState);
    }

    protected void onStop()
    {
        Log.d(TAG, "onStop");
        super.onStop();
    }

    public void surfaceCreated(SurfaceHolder holder)
    {
        Log.d(TAG, "surfaceCreated");
        mCamera = Camera.open();
        //mCamera.startPreview();
    }

    public void surfaceChanged(SurfaceHolder holder, int format, int w, int h)
    {
        Log.d(TAG, "surfaceChanged");

        // XXX stopPreview() will crash if preview is not running
        if (mPreviewRunning) {
            mCamera.stopPreview();
        }

        //setCameraParameters (w, h);
        try {
			mCamera.setPreviewDisplay(holder);
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
        mCamera.startPreview();
        mPreviewRunning = true;
    }

    /*
    private void setCameraParameters (int width, int height)
    {
        switch (Integer.valueOf(Build.VERSION.SDK)) {
            case 1:
            case 2:
            case 3:
            case 4:
                setCameraParameters_1_to_4 (width, height);
                break;
            case 5:
            case 6:
            case 7:
            default:
                setCameraParameters_5_to_7 (width, height);
                break;
        }
    }

    private void setCameraParameters_1_to_4 (int width, int height)
    {
        Camera.Parameters p = mCamera.getParameters();
        p.setPreviewSize(width,height);
        p.setPictureSize(640, 480);
        mCamera.setParameters(p);
    }

    private void setCameraParameters_5_to_7 (int width, int height)
    {
        Camera.Parameters p = mCamera.getParameters();
        // Get minimum dimensions greater than or equal to 640x480... Nexus 1
        // can go smaller. Probably cleaner way to do this...
        List<Camera.Size> sizes = p.getSupportedPictureSizes();
        int minsize = Integer.MAX_VALUE;    // hacky
        int minsizeIdx = 0;
        for (int i = 0; i < sizes.size(); i++) {
            if (sizes.get(i).width < 640) {
                continue;
            }
            if (minsize > sizes.get(i).width) {
                minsize = sizes.get(i).width;
                minsizeIdx = i;
            }
        }

        // if minsizeIdx == 0, then we did not find anything small but > 640x480
        // so just pick first one (since there will always be at least 1 result

        p.setPreviewSize(width, height);
        // assuming min sizes are in 0'th index
        p.setPictureSize(sizes.get(minsizeIdx).width,
                         sizes.get(minsizeIdx).height);

        Log.d(TAG, "Setting picture size: " +
        sizes.get(minsizeIdx).width + "x" + sizes.get(minsizeIdx).height);

        mCamera.setParameters(p);
    }
    */

    public void surfaceDestroyed(SurfaceHolder holder)
    {
        Log.d(TAG, "surfaceDestroyed");
        mCamera.stopPreview();
        mPreviewRunning = false;
        mCamera.release();
    }

    private SurfaceView mSurfaceView;
    private SurfaceHolder mSurfaceHolder;
}
