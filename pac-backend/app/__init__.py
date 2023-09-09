from flask import Flask, request, jsonify
import json
import pandas as pd
from io import StringIO
from .calculator import *
from .report_builder import *

APP = Flask(__name__)

@APP.route('/', methods=['POST'])
def upload():
    return jsonify(determinate(
        image= get_image(request.files['image']),
        post_process= json.loads(request.values.get('post_process'))
    ))

@APP.route('/result', methods=['POST'])
def report():
    return jsonify(build_report(
        sample_name= request.values['sample_name'],
        results= pd.read_json(StringIO(request.values['results'])),
        summary= pd.read_json(StringIO(request.values['summary'])),
        area_label= request.values['area_label'],
        images= json.loads(request.values['images']),
        comments= list(json.loads(request.values['comments']).keys())
    ))