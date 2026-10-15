import unittest
from server import apply_deal_price
class PriceMappingTests(unittest.TestCase):
    def test_price_by_execution_type(self):
        for kind,entry,exit in [(0,123.456,None),(1,None,123.456),(2,None,None),(3,None,123.456)]:
            row={};apply_deal_price(row,{'entry':kind,'price':123.456,'type':0})
            self.assertEqual(row['price'],123.456)
            self.assertEqual(row['entry'],entry)
            self.assertEqual(row['exit'],exit)
    def test_closing_execution_displays_original_position_direction(self):
        row={};apply_deal_price(row,{'entry':1,'price':4141.865,'type':0})
        self.assertEqual(row['side'],'Sell')
        self.assertEqual(row['dealSide'],'Buy')
        apply_deal_price(row,{'entry':1,'price':1.2,'type':1})
        self.assertEqual(row['side'],'Buy')
        self.assertEqual(row['dealSide'],'Sell')
if __name__=='__main__':unittest.main()
