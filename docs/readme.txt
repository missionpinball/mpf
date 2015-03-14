Sphinx-based documentation for the Mission Pinball Framework is available in the
build/html folder. Open index.html in a browser to view it. (Note the search
functionality is Javascript-based, so you can use it even if you're accessing
the files locally.)

The Sphinx documentation only includes the module reference. Full MPF
documentation is available online at http://missionpinball.com/docs.

If you extend the framework and want to re-generate your own documentation,
note that we use the numpydoc formatting style. More information and rationale
is here: http://codeandchaos.wordpress.com/2012/08/09/sphinx-and-numpydoc/

An example of the numpydoc docstring format is here:
https://github.com/numpy/numpy/blob/master/doc/example.py
(Or just browse the MPF source code to see how we do it)

We also originally used the sphinx-apidoc package to generate the .rst files.

Finally, if you do extend the framework, please share your changes with us so we
can incorporate them! Email us at brian@missionpinball.com.
