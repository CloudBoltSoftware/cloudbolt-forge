# This Python file uses the following encoding: utf-8
# The above line is required to support the use of unicode characters below.
from collections import namedtuple
from django.shortcuts import get_object_or_404, render

from common.methods import columnify
from extensions.views import dashboard_extension


@dashboard_extension()
# @dashboard_extension(title='Optional title', description='Optional description for admins')
def hello_world(request):
    """
    Describe the extension here or using the `description` kwarg to the
    decorator. This text is for admins and is displayed in tooltips on the
    Extensions Mgmt admin page.
    """
    # Prepare your data

    # A Greeting tuple has two properties, language and words:
    Greeting = namedtuple('Greeting', ['language', 'words'])
    greetings = [
        Greeting('Arabic', u'مرحبا بالعالم!'),
        Greeting('Armenian', u'Բարեւ, աշխարհ!'),
        Greeting('Bengali', u'ওহে বিশ্ব!'),
        Greeting('Chinese', u'你好，世界!'),
        Greeting('Danish', 'Hej Verden!'),
        Greeting('Deutsch', 'Hallo Welt!'),
        Greeting('English', 'Hello World!'),
        Greeting('French', 'Bonjour le monde!'),
        Greeting('Greek', u'Γειά σου Κόσμε!'),
        Greeting('Hebrew', u'שלום עולם!'),
        Greeting('Hindi', u'नमस्ते दुनिया!'),
        Greeting('Indonesian', 'Halo dunia!'),
        Greeting('Italiano', 'Ciao mondo!'),
        Greeting('Japanese', u'こんにちは世界!'),
        Greeting('Korean', u'안녕하세요 세계!'),
        Greeting('Lao', u'ສະ​ບາຍ​ດີ​ຊາວ​ໂລກ!'),
        Greeting('Persian', u'سلام دنیا!'),
        Greeting('Portuguese', u'Olá Mundo!'),
        Greeting('Russian', u'Привет мир!'),
        Greeting('Samoan', 'Talofa lalolagi!'),
        Greeting('Scottish Gaelic', 'Hàlo a Shaoghail!'),
        Greeting('Spanish', 'Hola Mundo!'),
        Greeting('Thai', u'สวัสดีชาวโลก!'),
        Greeting('Ukrainian', u'Привіт Світ!'),
        Greeting('Urdu', u'ہیلو دنیا!'),
        Greeting('Uzbek', 'Salom Dunyo!'),
        Greeting('Vietnamese', u'Chào thế giới!'),
        Greeting('Zulu', 'Sawubona Mhlaba!'),
    ]

    # The path to your template must include the extension package name,
    # here "hello_world_dashboard_ext".
    return render(request, 'hello_world_dashboard_ext/templates/hello.html', dict(
        # Pass data to the Django template as context variables.
        # More on templates:
        # https://docs.djangoproject.com/en/1.8/topics/templates/#the-django-template-language

        # Create columns of no more than 5 greetings
        columns=columnify(greetings, len(greetings) / 5),
    ))
