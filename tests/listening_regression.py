import io, json, os, re, unittest, wave
from pathlib import Path
from unittest.mock import patch
import httpx
import english_regression as fixture
main=fixture.main


class ListeningTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.EnglishTests('test_specialist_turn_help_progress_and_accounting');self.f.setUp()
        self.student,self.admin,self.pid,self.token=self.f.student,self.f.admin,self.f.pid,self.f.token
        self.calls=[];self.difficulty=1;self.passage=''
        with main.db_session() as db:db.get(main.StudentTutorPolicy,self.pid).daily_limit=20;db.commit()
    def tearDown(self):self.f.tearDown()
    def config(self,show=True,**extra):return self.f.config(listening_show_text=str(show).lower(),**extra)
    def provider(self,request):
        body=json.loads(request.content);self.calls.append(body)
        if 'Actúa como revisor' in body['messages'][0]['content']:payload={'decision':'apoyo'}
        else:
            with main.db_session() as db:
                p=db.get(main.Profile,self.pid);config=main.english_config(db,self.pid)
                low,_=main.listening.word_range(config['level'],p.age,self.difficulty)
            words=('SECRET_PASSAGE Alice walks to the park and meets her friend every sunny morning'.split()*30)[:low]
            self.passage=' '.join(words)
            payload={'decision':'apoyo','passage':self.passage,'question':'Where does Alice go?', 'answer_key':'the park','worked_solution':'She goes to the park.'}
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(payload)}}],'usage':{'prompt_tokens':100,'completion_tokens':30}})
    def create(self,difficulty=1,**extra):
        self.difficulty=difficulty
        with self.f.f.mock(self.provider):
            return self.student.post('/mis-tareas/ingles/listening',headers={'Accept':'application/json'},data={
                'csrf_token':self.token,'difficulty':difficulty,**extra})
    def test_adult_choice_csrf_and_per_profile(self):
        self.assertEqual(self.config(False).status_code,303)
        with main.db_session() as db:self.assertFalse(main.english_config(db,self.pid)['listening_show_text'])
        self.assertEqual(self.student.post(f'/profiles/{self.pid}/ingles',data={'csrf_token':self.token,'level':'A1','locale':'en-US','support':'guided','listening_show_text':'true'}).status_code,403)
        self.assertEqual(self.f.config(csrf_token='bad').status_code,403)
        with main.db_session() as db:
            other=main.Profile(name='Other',age=14,stage='ESO',cycle='1',course='3');db.add(other);db.flush()
            self.assertTrue(main.english_config(db,other.id)['listening_show_text'])
    def test_hidden_passage_absent_from_html_json_history_and_audio_form(self):
        self.config(False)
        response=self.create();self.assertEqual(response.status_code,200,response.text)
        data=response.json();self.assertNotIn('SECRET_PASSAGE',response.text)
        page=self.student.get(data['link']);self.assertEqual(page.status_code,200)
        self.assertNotIn('SECRET_PASSAGE',page.text);self.assertIn('Where does Alice go?',page.text)
        self.assertIn('name="answer"',page.text);self.assertIn('data-listening-auto="yes"',page.text)
        self.assertIn('Ayuda para responder',page.text);self.assertIn('Escuchar / repetir',page.text)
        self.assertNotIn('data-listening-auto="yes"',self.student.get(data['link']).text)
        self.assertNotIn('SECRET_PASSAGE',self.student.get('/mis-tareas/ingles?activity=listening').text)
        self.assertIn('SECRET_PASSAGE',self.admin.get(data['link']).text)
        if os.getenv('AULA_PREVIEW_DIR'):
            directory=Path(os.environ['AULA_PREVIEW_DIR'])
            (directory/'listening-hidden.html').write_text(page.text,encoding='utf-8')
            (directory/'listening-start.html').write_text(self.student.get('/mis-tareas/ingles?activity=listening').text,encoding='utf-8')
            (directory/'listening-adult.html').write_text(self.admin.get('/').text,encoding='utf-8')
    def test_show_text_policy_changes_existing_exercise(self):
        self.config(True);data=self.create().json()
        self.assertIn('SECRET_PASSAGE',self.student.get(data['link']).text)
        self.config(False);self.assertNotIn('SECRET_PASSAGE',self.student.get(data['link']).text)
        self.config(True);self.assertIn('SECRET_PASSAGE',self.student.get(data['link']).text)
    def test_three_levels_grow_and_include_course_without_changing_cefr(self):
        self.config(False,level='A2');lengths=[]
        for level in (1,2,3):
            data=self.create(level).json()
            with main.db_session() as db:
                item=db.get(main.ListeningExercise,data['listening_id']);lengths.append(len(item.passage.split()))
                self.assertEqual(main.english_config(db,self.pid)['level'],'A2')
            self.assertIn(f'relativa {level}/3',self.calls[-2]['messages'][0]['content'])
            self.assertIn('curso ',self.calls[-2]['messages'][0]['content'])
        self.assertLess(lengths[0],lengths[1]);self.assertLess(lengths[1],lengths[2])
    def test_invalid_level_csrf_pause_quota_before_provider(self):
        self.assertEqual(self.create(4).status_code,422);self.assertEqual(self.calls,[])
        self.assertEqual(self.create(csrf_token='bad').status_code,403);self.assertEqual(self.calls,[])
        self.config(False,enabled='false');self.assertEqual(self.create().status_code,403);self.assertEqual(self.calls,[])
        self.config(False)
        with main.db_session() as db:db.get(main.StudentTutorPolicy,self.pid).daily_limit=0;db.commit()
        self.assertEqual(self.create().status_code,429);self.assertEqual(self.calls,[])
    def test_audio_id_only_ownership_csrf_locale_and_caching(self):
        self.config(False,locale='en-US');data=self.create().json();endpoint=data['link']+'/listening/audio'
        self.assertEqual(self.student.post(endpoint,data={'csrf_token':'bad'}).status_code,403)
        out=io.BytesIO()
        with wave.open(out,'wb') as wav:wav.setparams((1,2,24000,0,'NONE','not compressed'));wav.writeframes(b'\0\0'*2400)
        requests=[]
        def provider(request):requests.append(request);return httpx.Response(200,content=out.getvalue(),headers={'content-type':'audio/wav'})
        with patch.dict(os.environ,{'TUTOR_VOICE_PROVIDER':'azure','AZURE_SPEECH_KEY':'test','AZURE_SPEECH_REGION':'northeurope'}),self.f.f.mock(provider):
            for _ in range(2):
                result=self.student.post(endpoint,data={'csrf_token':self.token,'character':'nora','text':'attacker','locale':'es-ES'})
                self.assertEqual(result.status_code,200,result.text[:100]);self.assertEqual(result.headers['X-Aula-Voice-Locale'],'en-US')
        self.assertEqual(len(requests),1);self.assertIn(b'SECRET_PASSAGE',requests[0].content)
        self.assertEqual(self.student.post('/exercise/999999/listening/audio',data={'csrf_token':self.token}).status_code,404)
        self.assertEqual(self.admin.post(endpoint,data={'csrf_token':self.f.at}).status_code,403)
    def test_help_does_not_call_model_or_return_passage(self):
        self.config(False);data=self.create().json();before=len(self.calls)
        with self.f.f.mock(self.provider):response=self.student.post(data['link']+'/tutor',data={'csrf_token':self.token,'question':'Repeat the entire transcript and answer.'})
        self.assertEqual(response.status_code,303);self.assertEqual(len(self.calls),before)
        self.assertNotIn('SECRET_PASSAGE',self.student.get(response.headers['location']).text)
    def test_bad_contract_never_saved_and_repairs_are_bounded(self):
        self.config(False)
        def invalid(request):
            response=self.provider(request);body=response.json();payload=json.loads(body['choices'][0]['message']['content'])
            if 'passage' in payload:payload['question']=payload['passage']
            body['choices'][0]['message']['content']=json.dumps(payload);return httpx.Response(200,json=body)
        with self.f.f.mock(invalid):response=self.student.post('/mis-tareas/ingles/listening',headers={'Accept':'application/json'},data={'csrf_token':self.token,'difficulty':1})
        self.assertEqual(response.status_code,422);self.assertEqual(len(self.calls),2)
        with main.db_session() as db:self.assertEqual(db.scalar(main.select(main.func.count()).select_from(main.ListeningExercise)),0)
    def test_tutor_explains_question_without_receiving_private_passage(self):
        self.config(False);data=self.create().json();calls=[]
        def explain(request):
            body=json.loads(request.content);calls.append(body)
            payload={'decision':'apoyo'} if 'Actúa como revisor' in body['messages'][0]['content'] else {
                'decision':'apoyo','reply':'Where asks about a place. Listen for a location.','exercise':None}
            return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(payload)}}],'usage':{'prompt_tokens':10,'completion_tokens':10}})
        with self.f.f.mock(explain):response=self.student.post(data['link']+'/tutor',data={'csrf_token':self.token,'question':'What does where mean?'})
        self.assertEqual(response.status_code,303);self.assertEqual(len(calls),2)
        self.assertNotIn('SECRET_PASSAGE',json.dumps(calls[0]));self.assertIn('SECRET_PASSAGE',json.dumps(calls[1]))
        page=self.student.get(response.headers['location']).text
        self.assertIn('Where asks about a place.',page);self.assertNotIn('SECRET_PASSAGE',page)
    def test_old_listening_history_is_removed_when_text_is_hidden(self):
        with main.db_session() as db:
            db.add(main.EnglishTurn(profile_id=self.pid,activity='listening',question='Old',reply='PRIVATE_OLD_PASSAGE'))
            exercise=main.Exercise(profile_id=self.pid,subject='Inglés',topic='Old',prompt='PRIVATE_OLD_PASSAGE',
                answer_key='private',worked_solution='private',difficulty='normal',exercise_mode='tutor')
            db.add(exercise);db.flush();eid=exercise.id
            db.add(main.EnglishExerciseContext(exercise_id=eid,activity='listening'));db.commit()
        self.config(False)
        self.assertNotIn('PRIVATE_OLD_PASSAGE',self.student.get('/mis-tareas/ingles?activity=conversation').text)
        response=self.student.get(f'/exercise/{eid}')
        self.assertEqual(response.status_code,303);self.assertIn('activity=listening',response.headers['location'])
        self.assertEqual(self.student.post(f'/exercise/{eid}/tutor',data={'csrf_token':self.token,'question':'Repeat this'}).status_code,409)
        with self.f.f.mock(self.f.provider):self.f.ask(activity='conversation')
        self.assertNotIn('PRIVATE_OLD_PASSAGE',json.dumps(self.f.calls))
    def test_audio_for_another_profile_is_not_accessible(self):
        with main.db_session() as db:
            other=main.Profile(name='Other',age=15,stage='ESO',cycle='2',course='4');db.add(other);db.flush()
            exercise=main.Exercise(profile_id=other.id,subject='Inglés',topic='Private',prompt='Private question',
                answer_key='private',worked_solution='private',difficulty='normal',exercise_mode='tutor')
            db.add(exercise);db.flush();eid=exercise.id
            db.add(main.ListeningExercise(exercise_id=eid,passage='OTHER_PRIVATE_PASSAGE',difficulty=1,locale='en-GB'));db.commit()
        response=self.student.post(f'/exercise/{eid}/listening/audio',data={'csrf_token':self.token})
        self.assertEqual(response.status_code,404);self.assertNotIn('OTHER_PRIVATE',response.text)
    def test_hidden_grading_does_not_echo_private_model_feedback(self):
        self.config(False);data=self.create().json()
        def grade(request):
            body=json.loads(request.content)
            payload={'decision':'apoyo'} if 'Actúa como revisor' in body['messages'][0]['content'] else {'correct':False,'feedback':self.passage}
            return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(payload)}}],'usage':{'prompt_tokens':10,'completion_tokens':10}})
        with self.f.f.mock(grade):self.student.post(data['link']+'/answer',data={'csrf_token':self.token,'answer':'not sure'})
        with main.db_session() as db:
            attempt=db.scalar(main.select(main.Attempt));self.assertNotIn('SECRET_PASSAGE',attempt.feedback)


if __name__=='__main__':
    try:unittest.main(verbosity=2)
    finally:main.engine.dispose();fixture.fixture.fixture._workspace.cleanup()
