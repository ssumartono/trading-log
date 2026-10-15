import copy, unittest
from server import merge_manual_edits
class MergeTests(unittest.TestCase):
    def test_sync_does_not_reject_or_lose_manual_note(self):
        base={'records':[{'id':1,'sourceKey':'a','note':'','strategy':'','indicator':'','profit':10,'price':100}], 'funds':[], 'brokers':[], 'settings':{'lastSync':'old','enabled':True},'syncRevision':1}
        current=copy.deepcopy(base);current['syncRevision']=2;current['settings']['lastSync']='new';current['records'][0]['profit']=12;current['records'][0]['price']=101;current['records'].append({'id':2,'sourceKey':'b','note':'','profit':7})
        edited=copy.deepcopy(base);edited['records'][0]['note']='Evaluasi';edited['records'][0]['indicator']='RSI';edited['records'][0]['price']=99
        result=merge_manual_edits(current,edited,base)
        self.assertEqual(len(result['records']),2);self.assertEqual(result['records'][0]['note'],'Evaluasi');self.assertEqual(result['records'][0]['price'],101);self.assertEqual(result['records'][0]['profit'],12);self.assertEqual(result['settings']['lastSync'],'new');self.assertEqual(result['syncRevision'],2)
    def test_same_manual_field_conflict_is_not_silently_overwritten(self):
        base={'records':[{'id':1,'note':'old'}],'funds':[],'brokers':[],'settings':{}}
        current=copy.deepcopy(base);current['records'][0]['note']='other'
        edited=copy.deepcopy(base);edited['records'][0]['note']='mine'
        with self.assertRaises(ValueError):merge_manual_edits(current,edited,base)
if __name__=='__main__':unittest.main()
