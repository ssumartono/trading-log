import sqlite3,unittest
from server import write_note
class NotesTests(unittest.TestCase):
    def test_crud_and_revision(self):
        db=sqlite3.connect(':memory:');db.execute('CREATE TABLE daily_notes(id INTEGER PRIMARY KEY AUTOINCREMENT,data TEXT,revision INTEGER DEFAULT 1)')
        draft={'title':'Evaluasi','body':'Catatan','eventDate':'2026-10-15T09:00','kind':'Memo','folder':'inbox','brokerId':None,'important':True}
        note=write_note(db,draft);self.assertEqual(note['revision'],1)
        edited=write_note(db,dict(note,body='Diperbarui'));self.assertEqual(edited['body'],'Diperbarui');self.assertEqual(edited['revision'],2)
        with self.assertRaises(ValueError):write_note(db,note)
        trash=write_note(db,dict(edited,folder='trash'));self.assertEqual(trash['folder'],'trash')
        restored=write_note(db,dict(trash,folder='inbox'));self.assertEqual(restored['folder'],'inbox')
        with self.assertRaises(ValueError):write_note(db,dict(draft,title=''))
        db.close()
if __name__=='__main__':unittest.main()
