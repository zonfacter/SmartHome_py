"""Local diagram/configuration endpoints, separate from all regulator writes."""
from flask import jsonify, render_template, request
from .heating_instrumentation import SetupError


def register_setup_routes(app,service):
    instrument=service.instrumentation
    def body(limit=200000):
        origin=request.headers.get('Origin')
        if not request.is_json or request.headers.get('X-Heating-Setup')!='1' or (origin and origin.rstrip('/')!=request.host_url.rstrip('/')):
            raise SetupError('Bitte die Einrichtung über diese SmartHome-Oberfläche speichern.',403)
        if request.content_length is None or request.content_length>limit:raise SetupError('Die Eingabe ist zu groß.',413)
        return request.get_json(silent=True)
    def response(data):
        result=jsonify(data);result.headers['Cache-Control']='no-store';return result
    def hours():
        try:value=int(request.args.get('hours','24'))
        except ValueError:raise SetupError('Ungültiger Zeitraum.')
        if value not in (1,6,24,168,720,2160):raise SetupError('Ungültiger Zeitraum.')
        return value
    @app.route('/heizung/anlagenplan')
    def heating_setup_page():
        service.start();return render_template('heating_setup.html',setup_page=True)
    @app.route('/api/heating/piping-plan',methods=['GET','PUT'])
    def heating_piping_plan():
        try:return response(instrument.save('plan',body()) if request.method=='PUT' else instrument.document('plan'))
        except SetupError as e:return jsonify({'message':str(e)}),e.status
    @app.route('/api/heating/instrumentation/config',methods=['GET','PUT'])
    def heating_instrumentation_config():
        try:
            result=instrument.save('sensors',body(12000)) if request.method=='PUT' else instrument.document('sensors')
            if request.method=='PUT':instrument.start()
            return response(result)
        except SetupError as e:return jsonify({'message':str(e)}),e.status
    @app.route('/api/heating/instrumentation')
    def heating_instrumentation_state():
        service.start();return response(instrument.snapshot())
    @app.route('/api/heating/instrumentation/history')
    def heating_instrumentation_history():
        try:return response(instrument.history(hours()))
        except SetupError as e:return jsonify({'message':str(e)}),e.status
    @app.route('/api/heating/instrumentation/diagnosis')
    def heating_instrumentation_diagnosis():
        try:return response(instrument.diagnosis(min(hours(),168)))
        except SetupError as e:return jsonify({'message':str(e)}),e.status
    @app.route('/api/heating/instrumentation/notes',methods=['GET','POST'])
    def heating_instrumentation_notes():
        try:return response(instrument.add_note(body(2048)) if request.method=='POST' else {'notes':instrument.notes()})
        except SetupError as e:return jsonify({'message':str(e)}),e.status
