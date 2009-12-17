''' MapSym '''

Sym_denom = {'':'','Team':'//','Sqd':'1','Sec':'2','Plt':'3','Coy':'4','Co':'4','Bn':'5','Rgt':'6','Bde':'7','Div':'8','Corp':'9','installation':'~'}

MapSym = {}
# Combat
MapSym[''] = ['0', 'Land']
MapSym['inf'] = ['I','Land']
MapSym['recce'] = ['L','Land']
MapSym['mech'] = ['M','Land']
MapSym['armor'] = ['A','Land']
MapSym['armor cav'] = ['R','Land']
MapSym['art'] = ['#','Land']
MapSym['sp-art'] = ['(','Land']
MapSym['HQ'] = [chr(172)+'0','Land']


# CSS
MapSym['CSS'] = ['S','Land']
MapSym['supply train'] = ['B','Land']
MapSym['convoy'] = ['B','Land']
MapSym['LOGPAC'] = ['c','Land']





for i in MapSym.values():
  i = [i,'Land']




