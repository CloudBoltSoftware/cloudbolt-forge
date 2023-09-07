# Django Cheatsheet
Django uses MTV (Model, Template, View) architecture

    Model - controls database
    Template - controls the way the webpage looks
    View - controls what happens via the code

How are these linked together and served to the browser?

Through the URLs:

    Specified in urls.py
    You hit the URL on the browser
    The request is forwarded to the urls.py
    The URL is matched to the method imported from the view
    The view imports the models


## [Django Query Resources](https://docs.djangoproject.com/en/3.2/ref/models/querysets/)
### Query Examples
```python
# Import the model
from myapp.models import MyModel

# Filter objects
filtered_objects = MyModel.objects.filter(field_name=value)

# Exclude objects
excluded_objects = MyModel.objects.exclude(field_name=value)

# Get first object
first_object = MyModel.objects.first()

# Get last object
last_object = MyModel.objects.last()

# Get latest object based on a specific field
latest_object = MyModel.objects.latest('field_name')
```

## [QuerySet API Reference](https://docs.djangoproject.com/en/3.2/ref/models/querysets/)





## [filter()](https://docs.djangoproject.com/en/3.2/ref/models/querysets/#filter)
filter is used to filter the queryset based on the field lookups specified. It returns a queryset of the objects that match the filter.

```python
# get a queryset for the server object named test
Server.objects.filter(hostname="test")

# get the first server object from the queryset for the server named test
Server.objects.filter(hostname="test").first()
```

## [exclude()](https://docs.djangoproject.com/en/3.2/ref/models/querysets/#exclude)
Use the exclude() method to remove items from queryset.

```python
# get all groups except for the group with name unassigned 
Group.objects.all().exclude(name="unassigned")
```


## [first()](https://docs.djangoproject.com/en/3.2/ref/models/querysets/#first)
```python
# First user object
User.objects.first()

```
## [get()](https://docs.djangoproject.com/en/3.2/ref/models/querysets/#get)
```python
# get the user object for the username of admin
User.objects.get(username="admin")
```

## [last()](https://docs.djangoproject.com/en/3.2/ref/models/querysets/#last)
```python
# Last user object
User.objects.last()

# Inspect user object attributes
user = User.objects.last()
user.__dict__
```


## Django Template Tags and Filters

When working with templates, you will need to use template tags and filters to manipulate the data that is being displayed.

You will encounter this if you are creating a custom template, for example a custom email template.   This is also useful when creating XUI components and reports.


### Built-in template tags and filters
https://docs.djangoproject.com/en/3.2/ref/templates/builtins/

[for](https://docs.djangoproject.com/en/3.2/ref/templates/builtins/#for)
The for tag is used to loop over a list of items. The items can be any iterable object, such as a list or QuerySet.
```django
{% for item in items %}
  <p>{{ item }}</p>
{% endfor %}

{% if user.is_authenticated %}
  <p>Welcome, {{ user.username }}!</p>
{% else %}
  <p>Please log in.</p>
{% endif %}
```

[if](https://docs.djangoproject.com/en/3.2/ref/templates/builtins/#if)
The if tag is used to evaluate a condition and display a block of content if the condition is true. The condition can be any expression that evaluates to True or False.

```django
{% if user.is_authenticated %}
  <p>Welcome, {{ user.username }}!</p>
{% else %}
  <p>Please log in.</p>
{% endif %}
```

