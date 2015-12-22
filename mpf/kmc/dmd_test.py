from kivy.app import App
from kivy.graphics.opengl import GL_RGBA, GL_RGB, GL_UNSIGNED_BYTE
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.graphics import Fbo, Color, Rectangle
from kivy.graphics.opengl import glReadPixels as py_glReadPixels
from kivy.uix.label import Label
from kivy.clock import Clock

import serial


class MediaController(Widget):

    def __init__(self, **kwargs):
        super(MediaController, self).__init__(**kwargs)

        self.add_widget(
            Button(
                text="Hello World",
                size_hint=(.5, .5),
                pos_hint={'center_x': .5, 'center_y': .5}))

from kivy.uix.widget import Widget

class FboTest(Widget):
    def __init__(self, **kwargs):
        super(FboTest, self).__init__(**kwargs)

        # first step is to create the fbo and use the fbo texture on other
        # rectangle

        self.serial = serial.Serial(port='com3', baudrate=2500000)

        with self.canvas:
            # create the fbo
            self.fbo = Fbo(size=(128, 32))

            # show our fbo on the widget in different size
            # Color(1, 1, 1)
            # Color(1, 0, 0, .8)
            # Rectangle(size=(10, 64))

        # in the second step, you can draw whatever you want on the fbo
        with self.fbo:

            # Rectangle(size=(32, 32), texture=self.fbo.texture)
            # Rectangle(pos=(32, 0), size=(64, 64), texture=self.fbo.texture)
            # Rectangle(pos=(96, 0), size=(128, 128), texture=self.fbo.texture)
            Label(text='MPF')

            Color(1, 0, 0, .8)
            Rectangle(size=(10, 10))
            # Color(0, 1, 0, .8)
            # Rectangle(size=(64, 256))



        Clock.schedule_interval(self.send, .1)

    def send(self, dt):

        print(dt)

        self.fbo.bind()
        data = py_glReadPixels(0, 0, 128, 32, GL_RGB, GL_UNSIGNED_BYTE)
        self.fbo.release()
        print(len(data))
        self.serial.write(bytearray([0x01]))
        self.serial.write(bytearray(data))
        # self.serial.close()

        # print len(data)

class MediaControllerApp(App):
    def build(self):
        return FboTest()


if __name__ == '__main__':
    MediaControllerApp().run()