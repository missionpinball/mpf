/*
    SmartMatrix Pinball DMD code for Teensy, based on:
    SmartMatrix Features Demo - Louis Beaudoin (Pixelmatix)
    This example code is released into the public domain
*/

#include <SmartLEDShieldV4.h> // this line must be first if using a V4 shield
#include <SmartMatrix3.h>
#include <usb_serial.h>

#define COLOR_DEPTH 24                  // known working: 24, 48 - If the sketch uses type `rgb24` directly, COLOR_DEPTH must be 24
const uint8_t kMatrixWidth = 128;       // known working: 32, 64, 96, 128
const uint8_t kMatrixHeight = 32;       // known working: 16, 32, 48, 64
const uint8_t kRefreshDepth = 24;       // known working: 24, 36, 48
const uint8_t kDmaBufferRows = 4;       // known working: 2-4, use 2 to save memory, more to keep from dropping frames and automatically lowering refresh rate
const uint8_t kPanelType = SMARTMATRIX_HUB75_32ROW_MOD16SCAN;   // use SMARTMATRIX_HUB75_16ROW_MOD8SCAN for common 16x32 panels
const uint8_t kMatrixOptions = (SMARTMATRIX_OPTIONS_NONE);      // see http://docs.pixelmatix.com/SmartMatrix for options
const uint8_t kBackgroundLayerOptions = (SM_BACKGROUND_OPTIONS_NONE);

SMARTMATRIX_ALLOCATE_BUFFERS(matrix, kMatrixWidth, kMatrixHeight, kRefreshDepth, kDmaBufferRows, kPanelType, kMatrixOptions);
SMARTMATRIX_ALLOCATE_BACKGROUND_LAYER(backgroundLayer, kMatrixWidth, kMatrixHeight, COLOR_DEPTH, kBackgroundLayerOptions);

const int defaultBrightness = 100*(255/100);    // full brightness
//const int defaultBrightness = 15*(255/100);    // dim: 15% brightness

const int defaultScrollOffset = 6;
const rgb24 defaultBackgroundColor = {0, 0, 0};

// Teensy 3.0 has the LED on pin 13
const int ledPin = 13;

boolean frameOn = false;
int dataPos = 0;
int dataExpected = 0;

bool gotCommand = false;
int commandPos = 0;

const int USB_MARKER_LENGTH = 4;
const int USB_COMMAND_LENGTH = 8;
const uint8_t usbMarker[USB_MARKER_LENGTH] = {0xBA, 0x11, 0x00, 0x03};
uint8_t usbCommand[USB_COMMAND_LENGTH];

// the setup() method runs once, when the sketch starts
void setup() {
  // initialize the digital pin as an output.
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);

  Serial.begin(2500000); // according to the Teensy docs this doesn't actually matter, will use USB speed

  matrix.addLayer(&backgroundLayer);
  matrix.begin();

  matrix.setBrightness(defaultBrightness);
  
  // clear screen
  backgroundLayer.fillScreen(defaultBackgroundColor);
  backgroundLayer.swapBuffers();
}


// the loop() method runs over and over again,
// as long as the board has power
uint16_t frameCount = 0;
void loop() {
  char* buffer = (char*)backgroundLayer.backBuffer();
  int bytesAvail = Serial.available();
  boolean swap = false;
  
  if ((bytesAvail > 1) && (dataPos > 0))
  {
    if (bytesAvail > dataExpected) bytesAvail = dataExpected;
    int count = Serial.readBytes(&buffer[dataPos], bytesAvail);
    dataPos += count;
    dataExpected -= count;
    if (dataExpected == 0) {
      swap = true;
    }
  }
  else if (bytesAvail) {
      char val = Serial.read();

   if (gotCommand)
   {
      buffer[dataPos++] = val;
      dataExpected--;
      if (dataExpected == 0) {
        swap = true;
      }
    }
   else if (commandPos < USB_MARKER_LENGTH) {
      usbCommand[commandPos] = val;
      if (usbCommand[commandPos] == usbMarker[commandPos]) {
        commandPos++;
      }
      else {
        commandPos = 0;
      }
    }
    else if (commandPos < USB_COMMAND_LENGTH) {
      usbCommand[commandPos] = val;
      commandPos++;
      if (commandPos >= USB_COMMAND_LENGTH)
      {
      gotCommand = true;
      backgroundLayer.swapBuffers(true);
      dataPos=0;
      dataExpected = kMatrixWidth * kMatrixHeight * 3;
      }
    }
  }

  if (swap) {
    frameCount++;
    gotCommand = false;
    commandPos = 0;
    char frameText[12];
    itoa(frameCount, frameText, 10);
    backgroundLayer.swapBuffers(true);
    dataPos = 0;
    dataExpected = kMatrixWidth * kMatrixHeight * 3;
    digitalWrite(ledPin, frameOn);
    frameOn = !frameOn;
  }
}
