# Python Primer

There are a few key things you should know to be able to effectively administer CloudBolt CMP with Python. For advanced Python usage, reference [the official python documentation](https://docs.python.org/)

Python is a general purpose programming language that has a guiding principle of being [human readable](https://peps.python.org/pep-0020/). Following these principles you should always keep in mind simplicity and reducing complexity.

## Syntax

Python is designed to be easily readable, as such it does not make heavy use of control characters.

This in mind, whitespace is very important, be mindful not to mix your tabs and spaces; when copying and pasting code from communication channels, be mindful that the character encoding may cause errors.
# Logic 
## [If / Else](https://docs.python.org/3/reference/expressions.html#conditional-expressions)

Ternary logic in Python is fairly straightforward.

```python
    if condition:
        print("true")
    else:
        print("false")
```


## [For loop](https://docs.python.org/3/tutorial/controlflow.html?highlight=loop#for-statements)
The most commmon iteration in Python is utilizing the For loop.
```python
    item_list = ['first', 'second','third']

    >>> for item in item_list:
    >>>     print(item)
    >>> first
    >>> second
    >>> third

```

## [Try ](https://docs.python.org/3/reference/compound_stmts.html#the-try-statement)
Try statements will allow you to dicate what happens on error, this will allow your code to execute without failure, or raise the failure.

```python
    try:
        print(foo)
    except Exception as e:
        print(f"An error occured: ")
        raise e
    finally:
        print("finally")
```
# Data Types
## [Boolean](https://docs.python.org/3/library/stdtypes.html#boolean-operations-and-or-not)
Boolean values in Python are True or False, with capital letters. 
```python
x = True 
y = False
>>> print(y is True)
>>> False
>>> print(x is True)
>>> True 
```

## [Strings](https://docs.python.org/3/library/stdtypes.html#string-methods)
Textual data in Python is handled with str objects, or strings. Strings are immutable sequences of Unicode code points. String literals are written in a variety of ways:

```python
Single quotes: 'allows embedded "double" quotes'

Double quotes: "allows embedded 'single' quotes"

Triple quoted: '''Three single quotes''', """Three double quotes"""
```


## [Lists](https://docs.python.org/3/library/stdtypes.html#lists)
Lists are mutable sequences, typically used to store collections of homogeneous items.

```python
list_item = []
list_item.append("first")
list_item.append("second")
>>> ['first', 'second']
```

## [Dictionaries](https://docs.python.org/3/library/stdtypes.html#dict)
Dictionaries provide key:value stores

```python
dict_item = {'key': 'value'}
# Add a new item to the dictionary
dict_item['newkey'] = 'newvalue'
>>> {'key': 'value', 'newkey': 'newvalue'}

```


# [Formatting Output](https://docs.python.org/3/tutorial/inputoutput.html#fancier-output-formatting)



## [F string](https://docs.python.org/3/tutorial/inputoutput.html#tut-f-strings)
F strings (Formatted String Literals) allow you to inject variables into a string.

```python
    year = 2016
    event = 'Referendum'

    >>> print(f'Results of the {year} {event}')
    >>> Results of the 2016 referendum

```

## ['str.format()'](https://docs.python.org/3/library/stdtypes.html#str.format)

Formatting a string can also be done with the (str.format()) method 
```python

    year = 2016
    event = 'Referendum'
    response = 'Results of the {} {}'.format(year,event)

    >>> print(response)
    >>> Results of the 2016 referendum

```

## [JSON](https://docs.python.org/3/library/json.html#module-json)
Python includes a json module to allow you to parse data into JSON format, this is handy especially for web requests.  It also allows you to load JSON data into a Python object.

String values representing JSON can be converted into dictionaries
```python
import json
json_from_web = '{"x": 1, "y": 2, "z": 3}'
target = json.loads(json_from_web)

>>> type(target)
<class 'dict'>
>>> target['x']
1
```

Inversely, dictionaries can be dumped to strings. 
#### [Loading JSON](https://docs.python.org/3/library/json.html#json.loads)
```python
import json

>>> json_string = json.dumps(target)
>>> type(json_string)
<class 'str'>
>>> json_string
'{"x": 1, "y": 2, "z": 3}'
```

## [Tuple](https://docs.python.org/3/library/stdtypes.html#tuples)

Tuples are immutable sequences, typically used to store collections of heterogeneous data.  Tuples can have any length. 

```python
tuple_item = ('one', 'two')
>>> ('one','two')

first_assignment, second_assignment = tuple_item
>>> print(first_assignment)
>>> 'one'
>>> print(second_assignment)
>>> 'second'

long_tuple = ('3','4','5','6','7')
>>> ('three','four','five','six','seven')


```

## [Class Objects](https://docs.python.org/3/tutorial/classes.html#class-objects)

A class is a collection of functions. Any object that is instantiated as a class will inherit all of the methods specified in that class.

```python
class MathClass:
    def add(self,x,y):
        response = x+y
        return response
    def subtract(self,x,y):
        response = x-y
        return response

```

You can instantiate an object as a class and it will inherit all of the methods.

```python
>>> math_obj = MathClass()
>>> math_obj.add(1,4)
>>> 5
>>> math_obj.subtract(5,4)
>>> 1  
```


## [Methods](https://docs.python.org/3/tutorial/classes.html#method-objects)

A method is a function specific to a class

```python
class MathClass:
    def method_in_class(self)
        return "I'm a method!"
```

## [Functions](https://docs.python.org/3/reference/compound_stmts.html#function)

A function is a collection of code that can be called, independently of a class. 

```python
def math_function(x, y): 
    return x+y

>>> math_function(1,2)
>>> 3
```

## [Pathing and Packages](https://docs.python.org/3/reference/import.html)

Python uses dot notation - this means referencing your folder paths with dots, rather than slashes (as a Linux shell would be)

The root folder of your project is the folder that contains your code, or in the case of a shell, the folder that you are in when you run the shell.

The following examples are for a project called 'my_project' in a folder called 'my_project' in the home directory of a user called 'user' for the unix path of /home/user/my_project, to simulate, you would run the following commands in a shell:

```bash
cd ~
mkdir my_project
cd my_project
touch my_module.py
mkdir my_folder
cd my_folder
touch my_module.py
mkdir my_subfolder
cd my_subfolder
touch my_module.py
```

```python
# This is a file in the root directory for the unix path of /home/user/my_project
import my_module


# This is a file in the root directory, in a folder called 'my_folder' for the unix path of /home/user/my_project/my_folder
import my_folder.my_module

# This is a file in the root directory, in a folder called 'my_folder', in a folder called 'my_subfolder' for the unix path of /home/user/my_project/my_folder/my_subfolder
import my_folder.my_subfolder.my_module

```

# Introspecting
The following methods will be useful for examining objects as you encounter them. 

## [vars](https://docs.python.org/3/library/functions.html#vars)
Return the __dict__ attribute for a module, class, instance, or any other object with a __dict__ attribute.
```python
class Person():
    def __init__(self,age,height):
        self.age = age
        self.height = height

>>> p = Person(11,5.4)
>>> vars(p)
{'age': 11, 'height': 5.4}
```

## [dir](https://docs.python.org/3/library/functions.html#dir)
The 'dir' method will reveal the methods that an object has access to - this is useful for finding out what methods are available to you.  

```python
class Person():
    def __init__(self,age,height):
        self.age = age
        self.height = height

dir(item)
>>> ['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', 'age', 'height']
```

## [type](https://docs.python.org/3/library/functions.html#type)
The 'type' method will reveal the type of an object. 

```python
class Person():
    def __init__(self,age,height):
        self.age = age
        self.height = height

>>> type(item)
<class '__main__.Person'>
```


