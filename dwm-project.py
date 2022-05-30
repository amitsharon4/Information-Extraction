import requests
import lxml.html
import rdflib
import sys
import re
import time

# Part one - Create ontology
WIKI_PREFIX = "http://en.wikipedia.org"
EXAMPLE_PREFIX = "http://example.org/"
PROBLEMATIC_CAPITAL = {"Vatican City": "", "Tokelau": "", "Caribbean Netherlands": "Willemstad",
                       "Antigua and Barbuda": "", "Mayotte": "Mamoudzou", "Macao": "", "Palestine": "Ramallah",
                       "Hong Kong": "", "Singapore": "Singapore", "Switzerland": "Bern", "Western Sahara": "Laayoune"}
PROBLEMATIC_GOVERNMENT = {"Réunion": "Overseas departments and regions of France", "Guadeloupe":
    "Overseas departments and regions of France", "Martinique":
                              "Overseas departments and regions of France", "French Guiana":
                              "Overseas departments and regions of France", "Mayotte":
                              "Overseas departments and regions of France",
                          "Channel Islands": "British Crown Dependency",
                          "Caribbean Netherlands": "Special Municipalities of the Netherlands"}
PROBLEMATIC_NAME = {'Abdul Hamid': 'Abdul Hamid (politician)'}
PROBLEMATIC_BIRTHDAY = {'Hasan Akhund': "c.1955 – c.1958", "Aziz Akhannouch": "1961", "Rashad al-Alimi": "1954",
                        "Maeen Abdulmalik Saeed": "1976", "Mohamed Béavogui": "15-08-1953", 'Félix Moloua': "",
                        'Cleopas Dlamini': "", "Mia Mottley": "", 'Carlos Vila Nova': ""}
PROBLEMATIC_BIRTHPLACE = {'Hasan Akhund': "Afghanistan", "Rashad al-Alimi": "Yemen", 'Moustafa Madbouly': "",
                          'Myint Swe': "", "Maeen Abdulmalik Saeed": "Yemen", "Mohamed Béavogui": "Guinea",
                          'Ariel Henry': "", 'Bisher Al-Khasawneh': "", 'Félix Moloua': "", 'Cleopas Dlamini': "",
                          'Carlos Vila Nova': "São Tomé and Príncipe", "Andrés Manuel López Obrador":
                              "Mexico"}
PROBLEMATIC_AREA = {"Israel": "20770-22072"}
PROBLEMATIC_PRESIDENT = {"Yemen": "Rashad al-Alimi", "Guam": "Joe Biden"}
graph = rdflib.Graph()
countries_dict = {}

"""fixing for ontology"""


def remove_prefix(fixed_name):
    return re.sub('_', ' ', fixed_name[len(EXAMPLE_PREFIX):])


def fixing_prefix(s):
    s = s.lstrip()
    res = re.sub('\s+', '_', s)
    return rdflib.URIRef(f'{EXAMPLE_PREFIX}{res}')


def first_letter(s):
    m = re.search(r'[a-z]', s, re.I)
    if m is not None:
        return m.start()
    return -1


def get_wiki_url(name):
    if name == "DR Congo":
        name = "Democratic Republic of the Congo"
    if name == "Palestine":
        name = "State of Palestine"
    if name == "Georgia":
        name = "Georgia (country)"
    if name == "Micronesia":
        name = "Federated States of Micronesia"
    if name == "Ireland":
        name = "Republic of Ireland"
    name = name.replace(" ", "_")
    return requests.get(WIKI_PREFIX + "/wiki/" + name)


def get_list_of_countries():
    res = requests.get("https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)")
    doc = lxml.html.fromstring(res.content)
    countries = []
    for i in range(2, 235):
        name = doc.xpath(
            "//*[@id='mw-content-text']/div[1]/table/tbody/tr[" + str(i) + "]/td[1]/descendant::a[1]//text()")[0]
        if name == "Congo":
            name = "DR Congo"
        countries.append(name)
    return countries


""" Receives a name of a person and returns the place and date of birth """


def get_personal_info(name, list_of_countries):
    if name in PROBLEMATIC_NAME:
        res = get_wiki_url(PROBLEMATIC_NAME[name])
    else:
        res = get_wiki_url(name)
    doc = lxml.html.fromstring(res.content)
    info_box = doc.xpath("//table[contains(@class, 'infobox')]")
    if not info_box:
        return {"Name": fixing_prefix(name), "POB": fixing_prefix(""), "DOB": fixing_prefix("")}
    born = info_box[0].xpath("//table//th[contains(text(), 'Born')]")
    if born:
        born_text = born[0].xpath("./../td/descendant-or-self::*/text()")
    try:
        dob = PROBLEMATIC_BIRTHDAY[name] if name in PROBLEMATIC_BIRTHDAY else born[0].xpath("./../td//span["
                                                                                        "@class='bday']//text("
                                                                                        ")")[0].replace(" ", "_")
    except IndexError:
        #born_text = born[0].xpath("./../td//text()")
        try:
            dob = next(line for line in born_text if re.compile("[0-9]+").search(line))
        except StopIteration:
            dob = ""
        dob = dob.replace(" ", "_")
    if name in PROBLEMATIC_BIRTHPLACE:
        pob = PROBLEMATIC_BIRTHPLACE[name]
    else:
        try:
            for entry in reversed(born_text):
                entry = entry.replace(',', "").replace(',', "").replace('[', "").replace(']', "").replace('(', "").\
                    replace(')', "")
                entry = entry.lstrip()
                if any(country in entry for country in list_of_countries):
                    pob = entry
                    break
            #pob = PROBLEMATIC_BIRTHPLACE[name] if name in PROBLEMATIC_BIRTHPLACE else born[0].xpath("./../td//a/text()")[0]
            if re.compile("[\d]").search(pob):
                raise IndexError
        except:
            try:
                pob = born[0].xpath("./../td/text()")[-1]
                if re.compile("[\d]").search(pob):
                    pob = born[0].xpath("./../td/text()")[-2]
            except IndexError:
                pob = ""
    pob = pob[first_letter(pob):].replace(" ", "_")
    return {"Name": fixing_prefix(name), "POB": fixing_prefix(pob), "DOB": fixing_prefix(dob)}


def get_government_type(info_box, curr_country):
    res = []
    try:
        if curr_country in PROBLEMATIC_GOVERNMENT:
            return res.append(fixing_prefix(PROBLEMATIC_GOVERNMENT[curr_country]))
        gov = info_box[0].xpath("(//tbody/tr[./descendant::*[text()='Government']])[1]/td[1]/"
                                "descendant::*/text()")
        if gov and "Seal" in gov[0]:
            gov = info_box[0].xpath("(//tbody/tr[./descendant::*[contains(text(), 'Government')]])[2]/td[1]/"
                                    "descendant::*/text()")
        if not gov:
            gov = info_box[0].xpath("(//tbody/tr[./descendant::*[contains(text(), 'Government')]])[1]/td/a/span/text()")
        gov_clean = []
        for s in gov:
            s = re.sub('[^a-zA-Z -]', '', s)
            if s != '' and not s.isspace() and len(s) > 1:
                gov_clean.append(s)
        for gov_type in gov_clean:
            res.append(fixing_prefix(gov_type))
    except IndexError:
        res.append(fixing_prefix(""))
    return res


def get_president(info_box, country_name):
    res = []
    if country_name in PROBLEMATIC_PRESIDENT:
        res.append(fixing_prefix(PROBLEMATIC_PRESIDENT[country_name]))
    else:
        try:
            #president = info_box[0].xpath("(//tbody/tr[./descendant::a[contains(text(), 'President')]])[1]/td/*[1]/text()")
            president = info_box[0].xpath(
                "(//tbody/tr[./descendant::a[./text()='President']])[1]/td/*[1]/text()")
            if not president:
                president = info_box[0].xpath(
                "(//tbody/tr[./descendant::a[./text()='President']])[1]/td/*[1]/*/text()")
            for entry in president:
                if entry not in res:
                    res.append(fixing_prefix(entry))
        except IndexError:
            res.append(fixing_prefix(""))
    return res


def get_pm(info_box):
    res = []
    try:
        pm = info_box[0].xpath("//tbody/tr[./descendant::a[contains(text(), 'Prime Minister')]]/td/a/text()")[0]
        res.append(fixing_prefix(pm))
    except IndexError:
        res.append(fixing_prefix(""))
    return res


def get_population(info_box, curr_country):
    res = []
    try:
        population = info_box[0].xpath("//tbody/tr[.//text() = 'Population']/td//text()")[0]
        if not re.compile("[\d]+[,]?[(]?[)]?[']?[ ]?").search(population):
            raise IndexError
    except IndexError:
        population = [info_box[0].xpath("//tbody/tr[.//text() = 'Population']/following::tr[1]/td//text()")[0]]
        try:
            population = next(word for word in population if re.compile("[\d]+[,]?[(]?[)]?[']?[ ]?").search(word))
        except StopIteration:
            population = info_box[0].xpath(
                "//tbody/tr[.//text() = 'Population']/following::tr[1]//*[not(self::img)]//text()")
            try:
                population = next(word for word in population if re.compile("[\d]+[,() ']?$").search(word))
            except:
                return res.append(fixing_prefix(""))
    population = population.lstrip()
    population = population.split(" ")[0] if " " in population else population
    population = population.replace('(', '').replace(')', '').replace("'", '')
    res.append(fixing_prefix(population))
    return res


def get_area(info_box, curr_country):
    res = []
    if curr_country in PROBLEMATIC_AREA:
        area_final = PROBLEMATIC_AREA[curr_country]
    else:
        try:
            area_raw = info_box[0].xpath("//tbody//tr[.//text()[contains(., 'Area')]]//td/text()")[0]
        except IndexError:
            area_raw = info_box[0].xpath("//tbody//tr[.//text()[contains(., 'Area')]]/following::tr[1]//td/text()")[0]
        if not re.compile('[\d][,]?[km]?[ ]?').search(area_raw[0]):
            area_raw = info_box[0].xpath("//tbody//tr[.//text()[contains(., 'Area')]]/following::tr[1]//td/text()")[0]
        area_final = ""
        if "mi" in area_raw:
            flag = False
            for word in area_raw.split():
                if flag:
                    if word == "km":
                        area_final += " "
                    area_final += word
                if word == "mi":
                    flag = True
        else:
            area_final = area_raw
        area_final = area_final.replace('(', '').replace(')', '').replace("'", '').replace("km", "")
        area_final += "_km_squared"
    res.append(fixing_prefix(area_final))
    return res


def get_capital(info_box, country_name):
    res = []
    if country_name in PROBLEMATIC_CAPITAL:
        capital = PROBLEMATIC_CAPITAL[country_name]
    else:
        try:
            capital = info_box[0].xpath("//tbody//tr[./th[contains(text(), 'Capital')]]/td//a[1]/text()")[0]
        except IndexError:
            capital = info_box[0].xpath("//tbody//tr[./th/a[contains(text(), 'Prefecture')]]/td//a[1]/text()")[0]
    res.append(fixing_prefix(capital))
    return res


""" Receives a name of a country and add to the dict the relevant info """


def get_country_info(name):
    res = get_wiki_url(name)
    doc = lxml.html.fromstring(res.content)
    info_box = doc.xpath("//table[contains(@class, 'infobox')]")
    return {
        "president_of": get_president(info_box, name),
        "prime_minister_of" : get_pm(info_box),
        "population_of": get_population(info_box, name),
        "area_of": get_area(info_box, name),
        "government_type": get_government_type(info_box, name),
        "capital_is": get_capital(info_box, name)
    }


def create():
    list_of_countries = get_list_of_countries()
    g = rdflib.Graph()
    for country in list_of_countries:
        info = get_country_info(country)
        for field in info.keys():
            if info[field]:
                if field == "president_of" or field == "prime_minister_of":
                    person_name = remove_prefix(info[field][0])
                    if person_name != '':
                        personal_details = get_personal_info(person_name, list_of_countries)
                        g.add((personal_details["POB"], fixing_prefix("pob"), info[field][0]))
                        g.add((personal_details["DOB"], fixing_prefix("dob"), info[field][0]))
                elif field == "government_type":
                    for gov_type in info[field]:
                        g.add((gov_type, fixing_prefix(field), fixing_prefix(country)))
                else:
                    g.add((info[field][0], fixing_prefix(field), fixing_prefix(country)))
    g.serialize("ontology.nt", format="nt", encoding="utf-8")
    sys.exit()


# Part two - question
def question(question):
    q=question.split(" ")
    ans=None
    flag=0
    if "president" in q or "prime" in q: #1,2,7-10
        if "president" in q:
            flag = 1
            if "born?" not in q: #Who is the president of <country>?
                x="_".join(q[5:])
                fix_country_q= x.rstrip(x[-1])
                ans=q_president_or_prime_of_country(fix_country_q,flag) #flag==1 president, else prime minister
            else:#When/Where was the president of <country> born?
                fix_country_q = "_".join(q[5:-1])
                if "When" in q: #When was the president of <country> born?
                    ans = q_president_or_prime_dob_pob(fix_country_q, flag,"dob")
                else: #Where was the president of <country> born?
                    ans = q_president_or_prime_dob_pob(fix_country_q, flag, "pob")
        else:
            if "born?" not in q: #Who is the prime minister of <country>?
                x="_".join(q[6:])
                fix_country_q= x.rstrip(x[-1])
                ans=q_president_or_prime_of_country(fix_country_q,flag) #flag==1 president, else prime minister
            else:#When/Where was the prime minister of <country> born?
                fix_country_q = "_".join(q[6:-1])
                if "When" in q: #When was the prime minister of <country> born?
                    ans = q_president_or_prime_dob_pob(fix_country_q, flag,"dob")
                else: #Where was the prime minister of <country> born?
                    ans = q_president_or_prime_dob_pob(fix_country_q, flag, "pob")

    elif "population" in q or "area" in q or "capital" in q: #What is the population of <country>? #3,4,6
        x = "_".join(q[5:])
        fix_country_q = x.rstrip(x[-1])
        if "population" in question:
            ans = q_mode(fix_country_q,"population_of")
        elif "area" in question:
            ans = q_mode(fix_country_q,"area_of")
        else :
            ans = q_mode(fix_country_q,"capital_is")
    elif "form" in question: #5. What is the form of government in <country>?
        x="_".join(q[7:])
        fix_country_q = x.rstrip(x[-1])
        ans = q_government_type(fix_country_q)

    elif "many" in q :
        #if "presidents" in q : #14. How many presidents were born in <country>?
            #x2= "_".join(q[5])
            #form2=x.rstrip(x[-1])
            #form1= "_".join(q[5])
            #fix_country_q = x.rstrip(x[-1])
            #ans = q_presidents_in_country(fix_country_q)
        #else: #12. How many <government_form1> are also <government_form2>?
            x = "_".join(q[6:])
            fix_country_q = x.rstrip(x[-1])
            #ans = How_many_government_form1_are_also_government_form2(form1, form2)





    return ans

def q_presidents_in_country(country):
    country_fix="<http://example.org/"+country+">"
    q="d"
    ans = g.query(q)
    if len(ans) == 0:
        print("no answer")
        exit()
    fix_ans=ans
    return fix_ans

def How_many_government_form1_are_also_government_form2(form1, form2):
    q = "d"
    ans = g.query(q)
    if len(ans) == 0:
        print("no answer")
        exit()
    fix_ans = ans

def q_government_type(country):
    country_fix="<http://example.org/"+country+">"
    q = "select ?x where " \
        "{ ?x <http://example.org/government_type>" + country_fix + " ." \
                                                     "}"
    ans = g.query(q)
    if len(ans) == 0:
        print("no answer")
        exit()
    fix_ans = str(str(list(ans)[0]).split("/")[-1]).replace(",", "").replace(")", "").replace('\'', "").replace("_", " ")
    return fix_ans

def q_mode(country,mode):
    country_fix="<http://example.org/"+country+">"
    q = "select ?x where " \
        "{ ?x <http://example.org/"+mode+">" + country_fix + " ." \
                                                     "}"
    ans = g.query(q)
    if len(ans) == 0:
        print("no answer")
        exit()
    fix_ans = str(str(list(ans)[0]).split("/")[-1]).replace(",", "").replace(")", "").replace('\'', "").replace("_", " ")
    return fix_ans


def q_president_or_prime_dob_pob(country,flag,mob):
    name=q_president_or_prime_of_country(country,flag)
    name=name.replace(" ","_")
    name_fix="<http://example.org/"+name+">"
    q = "select ?x where "\
        "{ ?x <http://example.org/"+mob+">" + name_fix + " ." \
        "}"
    ans = g.query(q)
    if len(ans) == 0:
        print("no answer")
        exit()
    fix_ans=str(str(list(ans)[0]).split("/")[-1]).replace(",", "").replace(")", "").replace('\'', "").replace("_", " ")
    return fix_ans


def q_president_or_prime_of_country(country,flag): #flag==1 president, else prime minister
    country_fix="<http://example.org/"+country+">"
    q_president= "select ?x where "\
        "{ ?x <http://example.org/president_of>" +country_fix+ " ."\
        "}"
    q_prime="select ?x where "\
        "{ ?x <http://example.org/prime_minister_of>" +country_fix+ " ."\
        "}"
    if flag==1:
        ans=g.query(q_president)
    else:
        ans = g.query(q_prime)
    if len(ans) == 0:
        print("no answer")
        exit()
    fix_ans=str(str(list(ans)[0]).split("/")[-1]).replace(",", "").replace(")", "").replace('\'', "").replace("_", " ")
    return fix_ans


create()

# Main
if len(sys.argv)==1:
    print("worng number of argument")
    exit()
if (sys.argv[1] == "create"):
    create()
    exit()
if (sys.argv[1] == "question"):
    if len(sys.argv) != 3:
        print("worng number of arguments for question mode")
        exit()
    else:
        g = rdflib.Graph()
        g.parse("ontology.nt", format="nt")
        ans=question(sys.argv[2])
        print(ans)
        exit()
