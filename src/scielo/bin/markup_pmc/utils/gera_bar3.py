
class Bar:
    def __init__(self):
        self.d = {}
        self.order = []
        self.names = {}
        self.texts = {}
    def organize_semantically(self):
    	for k,item in self.names.items():
    	    for k2,item2 in item.items():
    	        print k + ';'+ k2 + ';' + item2 
    	
    def organize_texts(self):
    	for k,item in self.texts.items():
    	    for item2 in item:
    	        print k + ';'+ item2 
    	
    def load_bars(self, file_name, lang):
        f = open(file_name, 'r')
        content = f.readlines()
        f.close()
        self.lang = lang
        for line in content:
            s = str(line)
            s = s.replace('\r\n','' )
            part = s.split(';')
            if len(part)>2:
                #traducoes
                item_name = part[0]
                k = group_name + ';' + item_name
                try:
                    self.d[k][lang] = part[1]
                except:
                    self.d[k] = {}
                    self.order.append(k)
                    self.d[k][lang] = part[1]
                if lang == 'pt':
                    try:
                        self.names[item_name][group_name] = part[1]
                    except:
                        self.names[item_name] = {}
                        self.names[item_name][group_name] = part[1]
                    
                    try:
                        self.texts[part[1]].append(item_name + ';' + group_name)
                    except:
                        self.texts[part[1]] = []
                        self.texts[part[1]].append(item_name + ';' + group_name)
            else:
                if len(part)==0:
                    #termina grupo
                    group_name = '' 
                else:
                    if part[0]!='down':
                        group_name = part[0]
                    else:
                        pass
    def write(self):
        for i in self.order:
            v = self.d[i]
            linha = i
            linha += ';pt;'
            try:
                linha += v['pt'] 
            except:
                linha += ''
            linha += ';' + 'Identifica <' + i[i.find(';')+1:] + '> de ' + '<' + i[0:i.find(';')] + '>'
            print linha
            
            linha = i
            linha += ';es;'
            try:
                linha += v['es'] 
            except:
                linha += ''
            linha += ';' + 'Identifica <' + i[i.find(';')+1:] + '> de ' + '<' + i[0:i.find(';')] + '>'
            print linha
            
            linha = i
            linha += ';en;'
            try:
                linha += v['en'] 
            except:
                linha += ''
            linha += ';' + 'Identify <' + i[i.find(';')+1:] + '> of ' + '<' + i[0:i.find(';')] + '>'
            print linha
            print '' 
            
bar = Bar()

bar.load_bars('../pt_bars.mds','pt')
bar.load_bars('../es_bars.mds','es')
bar.load_bars('../en_bars.mds','en')

bar.write()
bar.organize_semantically()
print '------'
bar.organize_texts()
        