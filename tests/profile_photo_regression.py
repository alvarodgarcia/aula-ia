import io, os, struct, unittest, zlib
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import english_regression as fixture
main=fixture.main


def image_bytes():
    out=io.BytesIO();image=Image.new('RGB',(640,480),'#9875bb')
    exif=Image.Exif();exif[315]='PRIVATE_METADATA';exif[274]=6
    image.save(out,format='JPEG',exif=exif);return out.getvalue()


class ProfilePhotoTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.EnglishTests('test_specialist_turn_help_progress_and_accounting');self.f.setUp()
        self.student,self.admin,self.pid,self.token=self.f.student,self.f.admin,self.f.pid,self.f.token
    def tearDown(self):self.f.tearDown()
    def allow(self,value=True):return self.admin.post(f'/profiles/{self.pid}/foto/permiso',data={'csrf_token':self.f.at,'allowed':str(value).lower()})
    def upload(self,data=None,**extra):return self.student.post('/mis-tareas/perfil/foto',data={'csrf_token':self.token,**extra},files={'photo':('user.jpg',image_bytes() if data is None else data,'image/jpeg')})
    def test_permission_off_by_default_and_adult_only(self):
        self.assertNotIn('name="photo"',self.student.get('/mis-tareas/perfil').text)
        self.assertEqual(self.upload().status_code,403)
        self.assertEqual(self.student.post(f'/profiles/{self.pid}/foto/permiso',data={'csrf_token':self.token,'allowed':'true'}).status_code,403)
        self.assertEqual(self.admin.post(f'/profiles/{self.pid}/foto/permiso',data={'csrf_token':'bad','allowed':'true'}).status_code,403)
        self.assertEqual(self.allow().status_code,303)
        self.assertIn('name="photo"',self.student.get('/mis-tareas/perfil').text)
    def test_photo_is_small_jpeg_without_original_metadata_and_no_ai(self):
        self.allow();self.assertEqual(self.upload().status_code,303)
        result=self.student.get(f'/profiles/{self.pid}/foto')
        self.assertEqual(result.status_code,200);self.assertIn('no-store',result.headers['cache-control'])
        self.assertEqual(result.headers['content-type'],'image/jpeg');self.assertNotIn(b'PRIVATE_METADATA',result.content)
        with Image.open(io.BytesIO(result.content)) as image:
            self.assertEqual(image.size,(320,320));self.assertEqual(dict(image.getexif()),{});self.assertEqual(image.mode,'RGB')
        self.assertLess(len(result.content),128*1024)
        with main.db_session() as db:
            self.assertEqual(db.scalar(main.select(main.func.count()).select_from(main.AIUsage)),0)
        self.assertEqual(self.admin.get(f'/profiles/{self.pid}/foto').status_code,200)
        if os.getenv('AULA_PREVIEW_DIR'):
            directory=Path(os.environ['AULA_PREVIEW_DIR'])
            (directory/'foto-perfil.html').write_text(self.student.get('/mis-tareas/perfil').text,encoding='utf-8')
            (directory/'foto-perfil-adulto.html').write_text(self.admin.get(f'/?alumno={self.pid}').text,encoding='utf-8')
            (directory/'foto-perfil-inicio.html').write_text(self.student.get('/mis-tareas').text,encoding='utf-8')
            (directory/'avatar-test.jpg').write_bytes(result.content)
    def test_csrf_ownership_and_anonymous_image_access(self):
        from fastapi.testclient import TestClient
        self.allow();self.upload()
        with TestClient(main.app) as anon:self.assertEqual(anon.get(f'/profiles/{self.pid}/foto').status_code,404)
        self.assertEqual(self.upload(csrf_token='bad').status_code,403)
        with main.db_session() as db:
            other=main.Profile(name='Other',age=16,stage='ESO',cycle='2',course='4');db.add(other);db.flush();oid=other.id
            db.add(main.ProfilePhoto(profile_id=oid,allowed=True,data=b'OTHER_PRIVATE_IMAGE'));db.commit()
        response=self.student.get(f'/profiles/{oid}/foto');self.assertEqual(response.status_code,404)
        self.assertNotIn(b'OTHER_PRIVATE_IMAGE',response.content)
        self.assertEqual(self.student.post(f'/profiles/{oid}/foto/eliminar',data={'csrf_token':self.token}).status_code,403)
    def test_revoking_permission_deletes_photo_and_disables_upload(self):
        self.allow();self.upload();self.allow(False)
        self.assertEqual(self.student.get(f'/profiles/{self.pid}/foto').status_code,404)
        with main.db_session() as db:
            item=db.get(main.ProfilePhoto,self.pid);self.assertFalse(item.allowed);self.assertIsNone(item.data)
        self.assertEqual(self.upload().status_code,403)
    def test_remove_as_owner_or_adult_keeps_permission(self):
        self.allow();self.upload()
        for client,token in ((self.student,self.token),(self.admin,self.f.at)):
            self.assertEqual(client.post(f'/profiles/{self.pid}/foto/eliminar',data={'csrf_token':token}).status_code,303)
            self.assertEqual(self.student.get(f'/profiles/{self.pid}/foto').status_code,404)
            with main.db_session() as db:self.assertTrue(db.get(main.ProfilePhoto,self.pid).allowed)
            self.upload()
        self.assertEqual(self.student.post(f'/profiles/{self.pid}/foto/eliminar',data={'csrf_token':'bad'}).status_code,403)
    def test_invalid_or_disguised_files_preserve_existing_photo(self):
        self.allow();self.upload();original=self.student.get(f'/profiles/{self.pid}/foto').content
        for content in (b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',b'%PDF-1.7',b'bad image'):
            self.assertEqual(self.upload(content).status_code,303)
            self.assertEqual(self.student.get(f'/profiles/{self.pid}/foto').content,original)
    def test_real_dimensions_and_encoded_size_are_bounded(self):
        def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',5001,5000,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00'*4))+chunk(b'IEND',b'')
        with self.assertRaisesRegex(ValueError,'resolución'):main.profile_photo.normalize(png)
        self.allow();self.assertEqual(self.upload(b'x'*(5*1024*1024+1)).status_code,303)
        response=self.student.post('/mis-tareas/perfil/foto',content=b'x'*(6*1024*1024+1))
        self.assertEqual(response.status_code,413)
    def test_upload_frequency_is_bounded_without_affecting_ai_quota(self):
        self.allow()
        for _ in range(6):self.assertEqual(self.upload().status_code,303)
        self.assertEqual(self.upload().status_code,429)
        with main.db_session() as db:self.assertEqual(db.scalar(main.select(main.func.count()).select_from(main.StudentAudit).where(main.StudentAudit.uses_quota.is_(True))),0)
    def test_permission_is_rechecked_after_decoding(self):
        self.allow();normalize=main.profile_photo.normalize
        def revoke(data):
            result=normalize(data)
            with main.db_session() as db:
                item=db.get(main.ProfilePhoto,self.pid);item.allowed=False;item.data=None;db.commit()
            return result
        with patch.object(main.profile_photo,'normalize',side_effect=revoke):self.assertEqual(self.upload().status_code,403)
        self.assertEqual(self.student.get(f'/profiles/{self.pid}/foto').status_code,404)


if __name__=='__main__':
    try:unittest.main(verbosity=2)
    finally:main.engine.dispose();fixture.fixture.fixture._workspace.cleanup()
