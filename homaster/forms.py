from django import forms


class EngawaForm(forms.Form):
    scenario_name = forms.CharField(label='シナリオ名')
    pc_num = forms.IntegerField(label='PC数')
    npc_num = forms.IntegerField(label='NPC数')
    ho_num = forms.IntegerField(label='HO数')