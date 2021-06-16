import os

from django.conf import settings
from django.core.management import call_command
from django.templatetags.static import static
from django.shortcuts import render
from django.utils.html import mark_safe
from extensions.views import dashboard_extension

from utilities.cb_http import parse_querystring_from_request
from utilities.decorators import json_view

from xui.bolty_cards.game import CardGame
from xui.bolty_cards.forms import GuessForm


@dashboard_extension
# @dashboard_extension(title='Optional title', description='Optional description for admins')
def bolty_card_game(request):

    # set up
    src = os.path.join(settings.PROSERV_DIR, "xui/bolty_cards/static/bolty_cards")
    dst = os.path.join(settings.PROSERV_DIR, "static/bolty_cards")

    try:
        os.symlink(src, dst)
        call_command('collectstatic', '--no-input')
    except FileExistsError:
        pass

    return render(request, 'bolty_cards/templates/cards.html', dict())

@json_view
def get_canvas(request):

    qs_dict = parse_querystring_from_request(request)
    game_string = None
    if qs_dict:
        game_string = list(qs_dict)[0]

    game = CardGame(game_string)
    first_4 = game.first_four.split("-")
    form = GuessForm(game=game).as_p()

    card_1 = static("bolty_cards/{}.png".format(first_4[0]))
    card_2 = static("bolty_cards/{}.png".format(first_4[1]))
    card_3 = static("bolty_cards/{}.png".format(first_4[2]))
    card_4 = static("bolty_cards/{}.png".format(first_4[3]))
    card_5 = static("bolty_cards/{}.png".format(game.guess))

    message = game.message

    template = """
    <div id="cards-row" class="row">
        <div id="card-1" class="col-md-2"><img src="{card_1}"/></div>
        <div id="card-2" class="col-md-2"><img src="{card_2}"/></div>
        <div id="card-3" class="col-md-2"><img src="{card_3}"/></div>
        <div id="card-4" class="col-md-2"><img src="{card_4}"/></div>
        <div id="card-5" class="col-md-2"><img src="{card_5}"/></div>
        <div id="extras" class="col-md-2">
            <div class="row" style="height: 100px;">
                {message}
            </div>
            <div class="row">
                {form}
            </div>
            <div class="row">
                <button id="check-it" type="button" class="btn btn-primary btn-sm">
                    Check it!
                </button>
                <button id="new-game" type="button" class="btn btn-secondary btn-sm">
                    <span class="btn-label"><i class="glyphicon glyphicon-refresh"></i></span>Reset
                </button>
                  <button class="btn btn-secondary btn-sm" type="button" data-toggle="modal" data-target="#exampleModalCenter">
                    <span class="btn-label"><i class="glyphicon glyphicon-info-sign"></i></span>
                  </button>
                  <!-- Modal -->
            </div>
        </div>
    </div>""".format(
        card_1=card_1, card_2=card_2, card_3=card_3, card_4=card_4, card_5=card_5,
        message=message, form=form
    ) + """
    <script>
        $('#new-game').on('click', function(event) {
            event.preventDefault(); // To prevent following the link (optional)
            load_game($('#game-canvas'), '');
        });
        $('#check-it').on('click', function(event) {
            var gameStr = $('#id_first_4').val() + '-' + $('#id_guess').val();
            event.preventDefault(); // To prevent following the link (optional)
            load_game($('#game-canvas'), gameStr);
        });
    </script>"""

    return {'content': mark_safe(template)}
