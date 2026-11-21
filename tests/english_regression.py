import io,json,os,unittest,wave
from pathlib import Path
from unittest.mock import patch
import httpx
import consumption_regression as fixture
main=fixture.main


class EnglishTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ConsumptionTests('test_student_attribution_internal_calls_and_no_duplicate');self.f.setUp()
        self.student,self.admin,self.pid,self.token,self.at=self.f.student,self.f.admin,self.f.pid,self.f.token,self.f.at
        self.calls=[]
    def tearDown(self):self.f.tearDown()
    def config(self,**extra):
        data={'csrf_token':self.at,'enabled':'true','level':'A2','locale':'en-GB','support':'guided','goal':'Everyday conversation'};data.update(extra)
        return self.admin.post(f'/profiles/{self.pid}/ingles',data=data)
    def provider(self,request):
        self.calls.append(json.loads(request.content));system=self.calls[-1]['messages'][0]['content']
        content={'decision':'apoyo'} if 'Actúa como revisor' in system else {
            'decision':'apoyo','reply':'What did you do yesterday?','exercise':None,
            'spanish_help':'Piensa en una actividad que hiciste ayer.',
            'learning':{'vocabulary':['yesterday','visited'],'feedback':'Hemos practicado preguntas sobre el pasado.'}}
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(content)}}],'usage':{'prompt_tokens':100,'completion_tokens':30}})
    def ask(self,**extra):
        data={'csrf_token':self.token,'study_mode':'english','activity':'conversation','question':'I visited my friend.'};data.update(extra)
        return self.student.post('/mis-tareas/tutor',data=data)
    def test_profile_configuration_requires_adult_csrf_and_valid_enums(self):
        self.assertEqual(self.config().status_code,303)
        with main.db_session() as db:self.assertEqual(main.english_config(db,self.pid)['level'],'A2')
        self.assertEqual(self.student.post(f'/profiles/{self.pid}/ingles',data={'csrf_token':self.token,'level':'C2','locale':'en-US','support':'english'}).status_code,403)
        self.assertEqual(self.config(csrf_token='bad').status_code,403)
        self.assertEqual(self.config(locale='https://example.invalid').status_code,422)
        self.assertEqual(self.config(level='expert').status_code,422)
    def test_specialist_turn_help_progress_and_accounting(self):
        self.config()
        with self.f.mock(self.provider):response=self.ask()
        self.assertEqual(response.status_code,303);self.assertIn('/mis-tareas/ingles',response.headers['location'])
        self.assertEqual(len(self.calls),2)
        self.assertIn('Nivel orientativo MCER: A2',self.calls[0]['messages'][0]['content'])
        self.assertNotIn('Responde en español conversacional',self.calls[0]['messages'][0]['content'])
        self.assertIn('Piensa en una actividad',self.calls[1]['messages'][1]['content'])
        with main.db_session() as db:
            turns=db.scalars(main.select(main.EnglishTurn)).all();self.assertEqual(len(turns),1)
            self.assertEqual(turns[0].profile_id,self.pid);self.assertIn('yesterday',turns[0].vocabulary)
            self.assertEqual(main.tutor_history(db,self.pid),[])
        self.assertEqual(main.accounting.report('mes')['providers']['openai']['totals']['text_tokens'],260)
        page=self.student.get('/mis-tareas/ingles?activity=listening')
        self.assertEqual(page.status_code,200);self.assertIn('Ver el texto de escucha',page.text)
        self.assertIn('Ayuda en español',page.text);self.assertIn('data-locale="en-GB"',page.text)
        if os.getenv('AULA_PREVIEW_DIR'):
            Path(os.environ['AULA_PREVIEW_DIR'],'ingles-alumno.html').write_text(page.text,encoding='utf-8')
            Path(os.environ['AULA_PREVIEW_DIR'],'ingles-adulto.html').write_text(self.admin.get(f'/?alumno={self.pid}').text,encoding='utf-8')
    def test_full_english_and_pause(self):
        self.config(support='english',locale='en-US')
        with self.f.mock(self.provider):self.ask()
        with main.db_session() as db:self.assertEqual(db.scalar(main.select(main.EnglishTurn)).spanish_help,'')
        self.config(enabled='false')
        self.calls=[]
        with self.f.mock(self.provider):self.ask()
        self.assertEqual(self.calls,[])
        self.assertIn('ha pausado',self.student.get('/mis-tareas/ingles').text)
    def test_invalid_activity_and_new_profile_never_inherits_level(self):
        self.assertEqual(self.student.get('/mis-tareas/ingles?activity=invalid').status_code,400)
        with self.f.mock(self.provider):self.assertEqual(self.ask(activity='invalid').status_code,400)
        self.assertEqual(self.calls,[])
        with main.db_session() as db:self.assertEqual(main.english_config(db,self.pid)['level'],'Por valorar')
    def test_validator_rejection_does_not_save_english_feedback(self):
        def reject(request):
            response=self.provider(request)
            if 'Actúa como revisor' in self.calls[-1]['messages'][0]['content']:
                return httpx.Response(200,json={'choices':[{'message':{'content':'{"decision":"tarea"}'}}],'usage':{'prompt_tokens':10,'completion_tokens':1}})
            return response
        with self.f.mock(reject):self.ask()
        with main.db_session() as db:self.assertEqual(db.scalar(main.select(main.func.count()).select_from(main.EnglishTurn)),0)
    def test_voice_locales_are_signed_escaped_cached_and_accounted(self):
        from xml.etree import ElementTree as ET
        out=io.BytesIO()
        with wave.open(out,'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\0\0'*2400)
        requests=[]
        def provider(request):requests.append(ET.fromstring(request.content));return httpx.Response(200,content=out.getvalue())
        text='Hello < friend & teacher.'
        with patch.dict(os.environ,{'TUTOR_VOICE_PROVIDER':'azure','AZURE_SPEECH_REGION':'northeurope','AZURE_SPEECH_KEY':'test-azure-key'}),self.f.mock(provider):
            def speak(locale,signature=None):return self.student.post('/tutor/voz',data={'csrf_token':self.token,'character':'nora','text':text,'locale':locale,'signature':signature or main.voice.voice_signature(self.pid,text,locale)})
            self.assertEqual(speak('en-US',main.voice.voice_signature(self.pid,text,'en-GB')).status_code,403)
            self.assertEqual(speak('en-GB').status_code,200)
            self.assertEqual(speak('en-US').status_code,200)
            self.assertEqual(speak('en-GB').status_code,200)
        self.assertEqual(len(requests),2)
        self.assertEqual([r.attrib['{http://www.w3.org/XML/1998/namespace}lang'] for r in requests],['en-GB','en-US'])
        self.assertEqual([r[0].attrib['name'] for r in requests],['en-GB-SoniaNeural','en-US-AriaNeural'])
        self.assertTrue(all(''.join(r.itertext())==text for r in requests))
        data=main.accounting.report('mes')['providers']['azure']['totals'];self.assertEqual(data['calls'],2);self.assertEqual(data['cache'],1)
    def test_spoken_english_returns_the_profile_locale(self):
        self.config(locale='en-US')
        from unittest.mock import AsyncMock
        with patch.object(main.voice,'transcribe_class_audio',new=AsyncMock(return_value='I visited a friend.')),self.f.mock(self.provider):
            response=self.student.post('/tutor/conversacion',data={'csrf_token':self.token,'character':'nora','study_mode':'english','activity':'conversation'},files={'audio':('turn.wav',b'mock','audio/wav')})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['locale'],'en-US')
        self.assertEqual(response.json()['signature'],main.voice.voice_signature(self.pid,response.json()['reply'],'en-US'))
        self.assertIn('Piensa',response.json()['english_help'])
    def test_other_profile_data_and_claimed_settings_are_not_used(self):
        with main.db_session() as db:
            other=main.Profile(name='Otro',age=16,stage='ESO',cycle='2.º ciclo',course='4.º');db.add(other);db.flush();other_id=other.id
            db.add(main.EnglishPreference(profile_id=other_id,level='C2',locale='en-US',goal='PRIVATE GOAL'))
            db.add(main.EnglishTurn(profile_id=other_id,activity='writing',question='PRIVATE QUESTION',reply='PRIVATE REPLY',spanish_help='PRIVATE HELP'));db.commit()
        page=self.student.get(f'/mis-tareas/ingles?profile_id={other_id}').text
        self.assertNotIn('PRIVATE',page)
        with self.f.mock(self.provider):self.ask(profile_id=other_id,level='C2',locale='en-US')
        self.assertIn('MCER: Por valorar',self.calls[0]['messages'][0]['content'])
        self.assertNotIn('PRIVATE',json.dumps(self.calls))
        with main.db_session() as db:self.assertEqual(db.scalar(main.select(main.func.count()).select_from(main.EnglishTurn).where(main.EnglishTurn.profile_id==self.pid)),1)
    def test_english_subject_exercises_keep_the_grading_contract(self):
        self.config(locale='en-US')
        with main.db_session() as db:
            exercise=main.Exercise(profile_id=self.pid,subject='Inglés',topic='Past simple',difficulty='adecuada',prompt='Complete: Yesterday I ___ to school.',answer_key='went',worked_solution='Go becomes went.',hints_json='[]',exercise_mode='tutor');db.add(exercise);db.commit();eid=exercise.id
        def grade(request):
            self.calls.append(json.loads(request.content))
            return httpx.Response(200,json={'choices':[{'message':{'content':'{"correct":true,"feedback":"Bien","score":100}'}}],'usage':{'prompt_tokens':50,'completion_tokens':10}})
        with self.f.mock(grade):result=self.student.post(f'/exercise/{eid}/answer',data={'csrf_token':self.token,'answer':'went'})
        self.assertEqual(result.status_code,303)
        self.assertIn('correct boolean',self.calls[0]['messages'][0]['content'])
        self.assertNotIn('incluye además learning',self.calls[0]['messages'][0]['content'])
        self.assertIn('data-locale="en-US"',self.student.get(f'/exercise/{eid}').text)
    def listening_provider(self, request):
        body=json.loads(request.content)
        self.calls.append(body)
        content={'decision':'apoyo'} if 'Actúa como revisor' in body['messages'][0]['content'] else {
            'decision':'apoyo','reply':'Try this exercise.','exercise':{'subject':'English','topic':'Listening',
            'prompt':'Listen: Alex went to the park. Where did Alex go? Write your answer below.',
            'answer_key':'the park','worked_solution':'Alex went to the park.', 'hints':[]}}
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(content)}}],'usage':{'prompt_tokens':100,'completion_tokens':30}})

    def test_listening_creation_speaks_instructions_and_entry_once(self):
        self.config(locale='en-US')
        with self.f.mock(self.listening_provider):
            response=self.student.post('/mis-tareas/tutor',headers={'Accept':'application/json'},data={
                'csrf_token':self.token,'study_mode':'english','activity':'listening','intent':'exercise','question':'Create a listening exercise.'})
        self.assertEqual(response.status_code,200)
        data=response.json()
        self.assertIn('Listen: Alex',data['reply']);self.assertIn('Write your answer below',data['reply'])
        self.assertNotIn('Alex went to the park.',data['reply'].split('Listen:')[0])
        self.assertEqual(data['locale'],'en-US')
        self.assertEqual(data['signature'],main.voice.voice_signature(self.pid,data['reply'],'en-US'))
        with main.db_session() as db:
            exercise=db.scalar(main.select(main.Exercise))
            self.assertEqual(db.get(main.EnglishExerciseContext,exercise.id).activity,'listening')
        page=self.student.get(data['link']).text
        self.assertIn('data-auto-target="exercise-listening-intro"',page)
        self.assertIn('data-locale="en-US"',page);self.assertIn('name="answer"',page)
        self.assertNotIn('data-auto-target="exercise-listening-intro"',self.student.get(data['link']).text)
        self.assertNotIn('data-auto-target="exercise-listening-intro"',self.admin.get(data['link']).text)
        self.assertEqual(len(self.calls),2)  # Opening/refreshing never asks the model again.
        if os.getenv('AULA_PREVIEW_DIR'):
            Path(os.environ['AULA_PREVIEW_DIR'],'escucha-ejercicio.html').write_text(page,encoding='utf-8')

    def test_listening_post_redirect_preserves_activity_and_pause(self):
        with self.f.mock(self.listening_provider):response=self.ask(activity='listening',intent='exercise')
        link=response.headers['location']
        with self.f.mock(self.provider):self.student.post(link+'/tutor',data={'csrf_token':self.token,'question':'Help me understand the instructions.'})
        self.assertIn('Habilidad: Escucha',self.calls[-2]['messages'][0]['content'])
        self.config(enabled='false')
        page=self.student.get(link).text
        self.assertNotIn('data-auto-target="exercise-listening-intro"',page)

    def test_listening_rejects_oversized_prompt_before_saving(self):
        def oversized(request):
            response=self.listening_provider(request)
            data=response.json();content=json.loads(data['choices'][0]['message']['content'])
            if content.get('exercise'):content['exercise']['prompt']='x'*1201
            data['choices'][0]['message']['content']=json.dumps(content)
            return httpx.Response(200,json=data)
        with self.f.mock(oversized):response=self.ask(activity='listening',intent='exercise')
        with main.db_session() as db:self.assertIsNone(db.scalar(main.select(main.Exercise)))
        self.assertEqual(response.status_code,303)

    def test_new_english_exercise_keeps_answer_field_and_subject(self):
        def provider(request):
            body=json.loads(request.content)
            content={'decision':'apoyo'} if 'Actúa como revisor' in body['messages'][0]['content'] else {
                'decision':'apoyo','reply':'Try this exercise.','exercise':{'subject':'Other','topic':'Past simple','prompt':'Complete: Yesterday I ___ to school.','answer_key':'went','worked_solution':'The past tense of go is went.','hints':['Think about an irregular verb.']}}
            return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(content)}}],'usage':{'prompt_tokens':100,'completion_tokens':30}})
        with self.f.mock(provider):result=self.ask(intent='exercise')
        self.assertTrue(result.headers['location'].startswith('/exercise/'))
        with main.db_session() as db:self.assertEqual(db.scalar(main.select(main.Exercise)).subject,'Inglés')
        page=self.student.get(result.headers['location']).text
        self.assertIn('name="answer"',page);self.assertIn('data-locale="en-GB"',page)


if __name__=='__main__':
    try:unittest.main(verbosity=2)
    finally:main.engine.dispose();fixture.fixture._workspace.cleanup()
