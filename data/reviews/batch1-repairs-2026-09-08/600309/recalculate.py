"""万华校准纠错复算，金额/比例严格分母一致。"""
import json
result=dict(cScore=sum([9,12,17,11,11,11]),mScore=sum([19,19,14,13,6,8,4]),target_price=69,valuation_certainty=.45,buy_price=69*(.68+.14*.45),ocf_parent=33105189455.82/12527201094.15,ocf_group=33105189455.82/14039935975.43,pledge_three=80000000/(677764654+330379594+301808357),pledge_two=80000000/(330379594+301808357),old_governance_bridge=(80-6-4)/85,new_governance_bridge=(83-6-4)/85,scenarios=[4.71*12,5.30*13,5.30*14])
if __name__=='__main__':print(json.dumps(result,ensure_ascii=False,indent=2))
