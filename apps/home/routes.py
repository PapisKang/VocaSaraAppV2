# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.home import blueprint
from flask import render_template, request
from flask_login import login_required
from jinja2 import TemplateNotFound


@blueprint.route('/index')
@login_required
def index():

    return render_template('home/index.html', segment='index')


@blueprint.route('/<template>')
@login_required
def route_template(template):
    print(template)
    try:

        if not template.endswith('.html'):
            template += '.html'

        # Detect the current page
        segment, active_menu, parent, segment_name = get_segment( request )

        # Serve the file (if exists) from app/templates/home/FILE.html
        return render_template(
            "home/" + template, 
            segment=segment, 
            active_menu=active_menu,
            parent=parent,
            segment_name=segment_name
        )

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404

    except:
        return render_template('home/page-500.html'), 500


# Helper - Extract current page name from request
def get_segment( request ): 

    try:

        segment     = request.path.split('/')[-1]
        active_menu = None
        parent = ""
        segment_name = ""

        core = segment.split('.')[0]
        

        if segment == '':
            segment     = 'index'
            active_menu = 'dashboard'

        if segment.startswith('dashboards-'):
            active_menu = 'dashboard'

        if segment.startswith('account-') or segment.startswith('users-') or segment.startswith('profile-') or segment.startswith('projects-'):
            active_menu = 'pages'

        if  segment.startswith('notifications') or segment.startswith('sweet-alerts') or segment.startswith('charts.html') or segment.startswith('widgets') or segment.startswith('messages'):
            active_menu = 'pages'     


        parent = core.split('-')[0] if core.split('-')[0] else ""
        segment_name = core


        return segment, active_menu, parent, segment_name

    except:
        return 'index', 'dashboard', '', ''  
