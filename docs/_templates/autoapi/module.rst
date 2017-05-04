{{ node.name }}
{{ '=' * node.name|length }}

.. automodule:: {{ node.name }}

   .. contents::
      :local:
{##}
{%- block modules -%}
{%- if subnodes %}

Submodules
----------

{% for item in subnodes %}
*  :doc:`{{ item.name }} <{{ item.name }}>`
{%- endfor %}
{##}
{%- endif -%}
{%- endblock -%}
{##}
.. currentmodule:: {{ node.name }}
{##}
{%- block functions -%}
{%- if node.functions %}

Functions
---------

{% for item, obj in node.functions.items() -%}
- :py:func:`{{ item }}`:
  {{ obj|summary }}

{% endfor -%}

{% for item in node.functions %}
.. autofunction:: {{ item }}
{##}
{%- endfor -%}
{%- endif -%}
{%- endblock -%}

{%- block classes -%}
{%- if node.classes %}

Classes
-------

{% for item, obj in node.classes.items() -%}
- :py:class:`{{ item }}`:
  {{ obj|summary }}

{% endfor -%}

{% for item in node.classes %}
.. autoclass:: {{ item }}
   :members:

{##}
{%- endfor -%}
{%- endif -%}
{%- endblock -%}

{%- block exceptions -%}
{%- if node.exceptions %}

Exceptions
----------

{% for item, obj in node.exceptions.items() -%}
- :py:exc:`{{ item }}`:
  {{ obj|summary }}

{% endfor -%}

{% for item in node.exceptions %}
.. autoexception:: {{ item }}

{##}
{%- endfor -%}
{%- endif -%}
{%- endblock -%}

{%- block variables -%}
{%- if node.variables %}

Variables
---------

{% for item, obj in node.variables.items() -%}
- :py:data:`{{ item }}`
{% endfor -%}

{% for item, obj in node.variables.items() %}
.. autodata:: {{ item }}
   :annotation:

.. code-block:: guess

   {{ obj|pprint|indent(3) }}
{##}
{%- endfor -%}
{%- endif -%}
{%- endblock -%}
