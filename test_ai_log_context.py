import unittest
from datetime import datetime,timezone
from ai_log_context import retrieve_logs
class LogContextTests(unittest.TestCase):
    def state(self):
        rows=[{'id':i+1,'broker':'A','date':'2026-10-15','time':'10:00','symbol':'XAUUSD','side':'Sell','profit':i-10,'ticket':str(100000+i),'orderId':'500000' if i==0 else '','note':'Evaluasi'} for i in range(80)]
        rows.append({'id':1000,'broker':'B','date':'2026-10-15','time':'10:00','symbol':'XAUUSD','profit':9999,'ticket':'100000'})
        return {'brokers':[{'id':1,'name':'A'},{'id':2,'name':'B'}],'records':rows}
    def test_all_summary_and_bounded_details_isolate_account(self):
        r=retrieve_logs(self.state(),{'brokerId':1,'logPeriod':'all'})
        self.assertEqual(r['logCount'],80);self.assertEqual(r['netProfit'],sum(i-10 for i in range(80)));self.assertLessEqual(r['detailCount'],40);self.assertTrue(r['detailsTruncated']);self.assertIn(1,[x['id'] for x in r['details']]);self.assertIn(80,[x['id'] for x in r['details']])
    def test_ticket_overrides_period_and_no_cross_account(self):
        r=retrieve_logs(self.state(),{'brokerId':1,'logPeriod':'day','eventDate':'2000-01-01','message':'evaluasi ticket 100000'})
        self.assertEqual(r['logCount'],1);self.assertEqual(r['details'][0]['id'],1)
        r=retrieve_logs(self.state(),{'brokerId':1,'logTicket':'500000'})
        self.assertEqual(r['logCount'],1)
    def test_wib_and_empty_invalid_ranges(self):
        now=datetime(2026,10,14,18,tzinfo=timezone.utc)
        self.assertEqual(retrieve_logs(self.state(),{'brokerId':1,'logPeriod':'today'},now)['logCount'],80)
        self.assertEqual(retrieve_logs(self.state(),{'brokerId':1,'logPeriod':'custom','logStart':'2020-01-01','logEnd':'2020-01-01'})['logCount'],0)
        with self.assertRaises(ValueError):retrieve_logs(self.state(),{'brokerId':1,'logPeriod':'custom','logStart':'2026-10-16','logEnd':'2026-10-15'})
    def test_three_days_inclusive_wib(self):
        state=self.state()
        state['records']=[dict(state['records'][0],id=i,date=date) for i,date in enumerate(['2026-10-12','2026-10-13','2026-10-14','2026-10-15'],1)]
        result=retrieve_logs(state,{'brokerId':1,'logPeriod':'3'},datetime(2026,10,14,18,tzinfo=timezone.utc))
        self.assertEqual(result['filters']['from'],'2026-10-13');self.assertEqual(result['filters']['to'],'2026-10-15');self.assertEqual(result['logCount'],3)
if __name__=='__main__':unittest.main()
