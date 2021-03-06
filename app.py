import sys
import os
import shutil
import time
import traceback
import json


from flask import Flask, request, jsonify, url_for, render_template
from flask.ext.navigation import Navigation
import pandas as pd
from sklearn.externals import joblib

app = Flask(__name__)
nav = Navigation(app)

# inputs
training_data = 'data/titanic_train.csv'
include = ['Age', 'Sex', 'Embarked', 'Survived']
dependent_variable = include[-1]

model_directory = 'model'
model_file_name = '%s/model.pkl' % model_directory
model_columns_file_name = '%s/model_columns.pkl' % model_directory

# These will be populated at training time
model_columns = None
clf = None

nav.Bar('top', [
    nav.Item('Home', 'index'),
    nav.Item('Train', 'train'),
    nav.Item('Wipe', 'wipe')
])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict_terminal', methods=['POST', 'GET'])
def predict_terminal():
    if os.listdir(model_directory) != []:
            json_ = json.dumps(request.json)
            json_ = json.loads(json_)

            query = pd.get_dummies(pd.DataFrame(json_['test']))

            for col in model_columns:
                if col not in query.columns:
                    query[col] = 0

            model = joblib.load(model_file_name)

            prediction = list(model.predict(query))
            #return jsonify({'prediction': prediction})
            f = open('output.txt', 'w')
            for pred  in prediction:
                f.write('%s\n' %pred)
            f.close()
            return render_template('prediction.html', preds = prediction)

    else:
        print 'train first'
        return 'no model here'


@app.route('/predict_form', methods=['POST', 'GET'])
def predict_form():
    if os.listdir(model_directory) != []:
        try:
            jsondata = request.form['jsondata']
            json_ = json.loads(jsondata)
            query = pd.get_dummies(pd.DataFrame(json_['test']))

            for col in model_columns:
                if col not in query.columns:
                    query[col] = 0

            model = joblib.load(model_file_name)

            prediction = list(model.predict(query))
            #return jsonify({'prediction': prediction})
            return render_template('prediction.html', preds = prediction)

        except Exception, e:

            return jsonify({'error': str(e), 'trace': traceback.format_exc()})
    else:
        print 'train first'
        return 'no model here'


@app.route('/train', methods=['GET'])
def train():
    # using random forest as an example
    # can do the training separately and just update the pickles
    from sklearn.ensemble import RandomForestClassifier as rf

    df = pd.read_csv(training_data)
    df_ = df[include]

    categoricals = []  # going to one-hot encode categorical variables

    for col, col_type in df_.dtypes.iteritems():
        if col_type == 'O':
            categoricals.append(col)
        else:
            df_[col].fillna(0, inplace=True)  # fill NA's with 0 for ints/floats, too generic

    # get_dummies effectively creates one-hot encoded variables
    df_ohe = pd.get_dummies(df_, columns=categoricals, dummy_na=True)

    x = df_ohe[df_ohe.columns.difference([dependent_variable])]
    y = df_ohe[dependent_variable]

    # capture a list of columns that will be used for prediction
    global model_columns
    model_columns = list(x.columns)
    joblib.dump(model_columns, model_columns_file_name)

    global clf
    clf = rf()
    start = time.time()
    clf.fit(x, y)
    print 'Trained in %.1f seconds' % (time.time() - start)
    print 'Model training score: %s' % clf.score(x, y)

    joblib.dump(clf, model_file_name, compress = 1)

    status = 'Success'
    estimators = clf.n_estimators

    return render_template('train.html', status = status, estimators = estimators)


@app.route('/wipe', methods=['GET'])
def wipe():
    try:
        shutil.rmtree('model')
        os.makedirs(model_directory)
        return render_template('wipe.html')

    except Exception, e:
        print str(e)
        return 'Could not remove and recreate the model directory'


if __name__ == '__main__':
    try:
        port = int(sys.argv[1])
    except Exception, e:
        port = 8080

    try:
        clf = joblib.load(model_file_name)
        print 'model loaded'
        model_columns = joblib.load(model_columns_file_name)
        print 'model columns loaded'

    except Exception, e:
        print 'No model here'
        print 'Train first'
        print str(e)
        clf = None



    app.run(port=port, debug=True)
