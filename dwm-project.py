import requests
import lxml.html
import rdflib
import sys
import re
from urllib.parse import unquote

# Part one - Create ontology
WIKI_PREFIX = "http://en.wikipedia.org"
EXAMPLE_PREFIX = "http://example.org/"
PROBLEMATIC_CAPITAL = {"Vatican_City": "", "Tokelau": "", "Caribbean_Netherlands": "Willemstad",
                       "Antigua_and_Barbuda": "", "Mayotte": "Mamoudzou", "Macau": "", "State_of_Palestine": "Ramallah",
                       "Hong_Kong": "", "Singapore": "Singapore", "Switzerland": "Bern", "Western_Sahara": "Laayoune",
                       "Réunion": "Saint-Denis,_Réunion"}
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
                          'Carlos Vila Nova': "São Tomé and Príncipe","Patrice Talon": "Dahomey",
                          "Andrés Manuel López Obrador": "Mexico", "Mahmoud Abbas": "Mandatory Palestine"}
PROBLEMATIC_AREA = {"Israel": "20770-22072"}
PROBLEMATIC_PRESIDENT = {"Yemen": "Rashad al-Alimi", "Guam": "Joe Biden"}
graph = rdflib.Graph()
countries_dict = {}

"""fixing for ontology"""


def remove_prefix(fixed_name):
    return re.sub('_', ' ', fixed_name[len(EXAMPLE_PREFIX):])


def remove_wiki_prefix(uri):
    return re.sub("/wiki/", "", uri)


def is_wiki_uri(uri):
    return '/wiki' in uri


def fixing_prefix(s):
    s = s.strip()
    res = re.sub('\s+', '_', s)
    return rdflib.URIRef(f'{EXAMPLE_PREFIX}{res}')


def first_letter(s):
    m = re.search(r'[a-z]', s, re.I)
    if m is not None:
        return m.start()
    return -1


def get_wiki_url(name):
    name = name.replace(" ", "_")
    return requests.get(WIKI_PREFIX + "/wiki/" + name)


def get_country_name_from_url(name):
    doc = lxml.html.fromstring(get_wiki_url(name).content)
    return doc.xpath("//h1/text()")[0]


def get_list_of_countries():
    res = requests.get("https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)")
    doc = lxml.html.fromstring(res.content)
    countries = []
    for i in range(2, 235):
        name = doc.xpath(
            "//*[@id='mw-content-text']/div[1]/table/tbody/tr[" + str(i) + "]/td[1]/descendant::a[1]//@href")[0]
        name = unquote(name)
        name = remove_wiki_prefix(name)
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
        try:
            dob = next(line for line in born_text if re.compile("[0-9]+").search(line))
        except StopIteration:
            dob = ""
        dob = dob.replace(" ", "_")
    if name in PROBLEMATIC_BIRTHPLACE:
        pob = PROBLEMATIC_BIRTHPLACE[name]
    else:
        try:
            pob = born[0].xpath("./../td/descendant-or-self::a/@href")[-1]
            if pob and is_wiki_uri(pob):
                pob = unquote(pob)
                pob = remove_wiki_prefix(pob)
            else:
                for entry in reversed(born_text):
                    entry = entry.replace(',', "").replace(',', "").replace('[', "").replace(']', "").replace('(', ""). \
                        replace(')', "")
                    entry = entry.strip()
                    if any(country in entry for country in list_of_countries) or "USSR" in entry or "Soviet Union" in entry:
                        pob = entry
                        break
                if re.compile("[\d]").search(pob):
                    raise IndexError
        except:
            try:
                pob = born[0].xpath("./../td/text()")[-1]
                if re.compile("[\d]").search(pob):
                    pob = born[0].xpath("./../td/text()")[-2]
            except IndexError:
                pob = ""
    pob = pob.strip()
    pob = pob[first_letter(pob):].replace(" ", "_")
    return {"Name": fixing_prefix(name), "POB": fixing_prefix(pob), "DOB": fixing_prefix(dob)}


def get_government_type(info_box, curr_country):
    res = []
    try:
        if curr_country in PROBLEMATIC_GOVERNMENT:
            return res.append(fixing_prefix(PROBLEMATIC_GOVERNMENT[curr_country]))
        gov = info_box[0].xpath("(//tbody/tr[./descendant::*[text()='Government']])[1]/td[1]/"
                                "descendant::a/@href")
        if gov and "Seal" in gov[0]:
            gov = info_box[0].xpath("(//tbody/tr[./descendant::*[contains(text(), 'Government')]])[2]/td[1]/"
                                    "descendant::a/@href")
        if not gov:
            gov = info_box[0].xpath("(//tbody/tr[./descendant::*[contains(text(), 'Government')]])[1]/td//@href")
        gov_clean = []
        for s in gov:
            if is_wiki_uri(s):
                s = unquote(s)
                s = remove_wiki_prefix(s)
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


def get_population(info_box):
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
    population = population.strip()
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
        area_final = area_final.strip()
    area_final += "_km_squared"
    res.append(fixing_prefix(area_final))
    return res


def get_capital(info_box, country_name):
    res = []
    if country_name in PROBLEMATIC_CAPITAL:
        capital = PROBLEMATIC_CAPITAL[country_name]
    else:
        try:
            capital = info_box[0].xpath("//tbody//tr[./th[contains(text(), 'Capital')]]/td//a[1]/@href")[0]
        except IndexError:
            capital = info_box[0].xpath("//tbody//tr[./th/a[contains(text(), 'Prefecture')]]/td//a[1]/@href")[0]
        capital = unquote(capital)
        capital = remove_wiki_prefix(capital)
    res.append(fixing_prefix(capital))
    return res


""" Receives a name of a country and add to the dict the relevant info """


def get_country_info(name):
    res = get_wiki_url(name)
    doc = lxml.html.fromstring(res.content)
    info_box = doc.xpath("//table[contains(@class, 'infobox')]")
    return {
        "president_of": get_president(info_box, name),
        "prime_minister_of": get_pm(info_box),
        "population_of": get_population(info_box),
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
                if field == "government_type":
                    for gov_type in info[field]:
                        g.add((gov_type, fixing_prefix(field), fixing_prefix(country)))
                else:
                    g.add((info[field][0], fixing_prefix(field), fixing_prefix(country)))
    g.serialize("ontology.nt", format="nt", encoding="utf-8")
    sys.exit()



"""  Part two - SPARQL queris  """


def question(question):
    q = question.split(" ")
    flag = 0
    if ("president" in q or "prime" in q) and "countries" not in q:  # 1,2,7-10
        if "president" in q:
            flag = 1
            if "Who" in q:  # Who is the president of <country>?
                x = "_".join(q[5:])
                fix_country_q = x.rstrip(x[-1])
                ans = q_president_or_prime_of_country(fix_exmaple(fix_country_q),
                                                      flag)  # flag==1 president, else prime minister
            else:  # When/Where was the president of <country> born?
                fix_country_q = "_".join(q[5:-1])
                if "When" in q:  # When was the president of <country> born?
                    ans = q_president_or_prime_dob_pob(fix_exmaple(fix_country_q), flag, "dob")
                else:  # Where was the president of <country> born?
                    ans = q_president_or_prime_dob_pob(fix_exmaple(fix_country_q), flag, "pob")
        else:
            if "Who" in q:  # Who is the prime minister of <country>?
                x = "_".join(q[6:])
                fix_country_q = x.rstrip(x[-1])
                ans = q_president_or_prime_of_country(fix_exmaple(fix_country_q),
                                                      flag)  # flag==1 president, else prime minister
            else:  # When/Where was the prime minister of <country> born?
                fix_country_q = "_".join(q[6:-1])
                if "When" in q:  # When was the prime minister of <country> born?
                    ans = q_president_or_prime_dob_pob(fix_exmaple(fix_country_q), flag, "dob")
                else:  # Where was the prime minister of <country> born?
                    ans = q_president_or_prime_dob_pob(fix_exmaple(fix_country_q), flag, "pob")

    elif "population" in q or "area" in q or ("capital" in q and "countries" not in q) :  # What is the population/area/capital of <country>? #3,4,6
        x = "_".join(q[5:])
        fix_country_q = x.rstrip(x[-1])
        if "population" in question:
            ans = q_mode(fix_exmaple(fix_country_q), "population_of")
        elif "area" in question:
            ans = q_mode(fix_exmaple(fix_country_q), "area_of")
        else:
            ans = q_mode(fix_exmaple(fix_country_q), "capital_is")

    elif "form" in question:  # 5. What is the form of government in <country>?
        x = "_".join(q[7:])
        fix_country_q = x.rstrip(x[-1])
        ans = q_government_type(fix_exmaple(fix_country_q))

    elif "many" in q:
        if "presidents" in q:  # 14. How many presidents were born in <country>?
            x = "_".join(q[6:])
            fix_country_q = x.rstrip(x[-1])
            ans = q_presidents_in_country(fix_exmaple(fix_country_q))
        else:  # 12. How many <government_form1> are also <government_form2>?
            many_i = q.index("many")
            are_i = q.index("are")
            also_i = q.index("also")
            form1 = "_".join(q[many_i + 1:are_i])
            x2 = "_".join(q[also_i + 1:])
            form2 = x2.rstrip(x2[-1])
            ans = How_many_government_form1_are_also_government_form2(fix_exmaple(form1), fix_exmaple(form2))

    elif "countries" in q and "List" in q:  # 13List all countries whose capital name contains the string <str>
        string = q[9]
        ans = q_list_countries_contains_str(string)
    elif "Who" in q and "president" not in q and "prime" not in q:  # 11. Who is <entity>?
        x = "_".join(q[2:])
        entity_fix = x.rstrip(x[-1])
        ans = q_entity(fix_exmaple(entity_fix))

    else:  # The capital of which countries is <capital>?
        x = "_".join(q[6:])
        fix_q = x.rstrip(x[-1])
        ans = q_the_capital_of_which_countries(fix_exmaple(fix_q))

    return ans


"""  fixing for questions  """


def fix_ans(q,flag):
    if len(q) == 0 and flag==0:
        print("no answer")
        exit()
    else:
        res = []
        for c in list(q):
            fix = str(str(list(c)[0]).split("/")[-1]).replace(")", "").replace('\'', "").replace("_", " ")

            res.append(fix)

        res.sort()
        res = ", ".join(res)

    return res


def fix_exmaple(name):
    return "<http://example.org/" + name + ">"

def fix_entity(q):
    if len(q) == 0:
        print("no answer")
        exit()
    else:
        res = []
        for c in list(q):
            fix = str(str(list(c)[0]).split("/")[-1]).replace(")", "").replace('\'', "").replace("_", " ")
            res.append(fix)
            res.sort()
        return res

"""  SPARQL queris  """


# 13. List all countries whose capital name contains the string <str>
def q_list_countries_contains_str(string):
    q = "select ?x where " \
        "{?y <http://example.org/capital_is> ?x ." \
        "FILTER(CONTAINS(lcase(str(?y)), '" +string+ "')) . " \
        "}"
    ans = g.query(q)
    list_countries=fix_ans(ans,1)
    if len(list_countries) == 0:
        return "No countries"
    return list_countries


# The capital of which countries is <capital>?
def q_the_capital_of_which_countries(name):
    q = "select ?x where " \
        "{ " + name + "<http://example.org/capital_is> ?x ." \
                      "}"

    ans = g.query(q)
    return fix_ans(ans,0)


# 11. Who is <entity>?
def q_entity(entity):
    res=""
    q_president_of = "select ?x where " \
        "{ " + entity + "<http://example.org/president_of> ?x ." \
                      "}"
    q_prime_of = "select ?x where " \
        "{ " + entity + "<http://example.org/prime_minister_of> ?x ." \
                      "}"
    ans_president = g.query(q_president_of)
    ans_prime = g.query(q_prime_of)

    if len(ans_prime) == 0 and len(ans_president) == 0:
        print("no answer")
        exit()
    elif len(ans_prime) != 0 and len(ans_president) == 0:  # prime minister
        ans = fix_entity(ans_prime)
        for a in ans:
            res+= "Prime Minister of " +a+", "
        return res[:-2]
    elif len(ans_prime) == 0 and len(ans_president) != 0:  # president
        ans = fix_entity(ans_president)
        for a in ans:
            res+= "President of " + a+", "
        return res[:-2]
    else:
        ans_1p = fix_entity(ans_president)
        ans_2p = fix_entity(ans_prime)
        for a in ans_1p:
            res+= "President of " + a+", "
        for a in ans_2p:
            res+="Prime Minister of " +a+", "
        return res[:-2]


# 14. How many presidents were born in <country>?
def q_presidents_in_country(country):
    q = "select ?x where " \
        "{" + country + " <http://example.org/pob> ?x ." \
        " ?x <http://example.org/president_of> ?y . " \
        "}"
    ans = g.query(q)

    num= fix_ans(ans,1).split(",")
    if len(num[0]) == 0 :
        return 0

    return len(num)


# 12. How many <government_form1> are also <government_form2>?
def How_many_government_form1_are_also_government_form2(form1, form2):
    q_form1 = "select ?x where " \
              "{ " + form1 + "<http://example.org/government_type> ?x ." \
                             "}"
    q_form2 = "select ?x where " \
              "{ " + form2 + "<http://example.org/government_type> ?x ." \
                             "}"
    ans_form1 = g.query(q_form1)
    ans_form2 = g.query(q_form2)
    res_form1 = fix_ans(ans_form1,0)
    res_form2 = fix_ans(ans_form2,0)
    return list(set(res_form1) & set(res_form2))


# 5. What is the form of government in <country>?
def q_government_type(country):
    q = "select ?x where " \
        "{ ?x <http://example.org/government_type>" + country + " ." \
                                                                "}"
    ans = g.query(q)
    return fix_ans(ans,0)


# 3. What is the population of <country>?
# 4. What is the area of <country>?
# 6. What is the capital of <country>?
def q_mode(country, mode):
    q = "select ?x where " \
        "{ ?x <http://example.org/" + mode + ">" + country + " ." \
                                                             "}"

    ans = g.query(q)
    return fix_ans(ans,0)


# 9. When was the prime minister/president of <country> born?
# 10. Where was the prime minister/president of <country> born?
def q_president_or_prime_dob_pob(country, flag, mob):
    name = q_president_or_prime_of_country(country, flag)
    name = name.replace(" ", "_")
    q = "select ?x where " \
        "{ ?x <http://example.org/" + mob + ">" + fix_exmaple(name) + " ." \
                                                                      "}"
    ans = g.query(q)
    return fix_ans(ans,0)


# 1. Who is the president of <country>?
# 2. Who is the prime minister of <country>?
def q_president_or_prime_of_country(country, flag):  # flag==1 president, else prime minister
    q_president = "select ?x where " \
                  "{ ?x <http://example.org/president_of>" + country + " ." \
                                                                       "}"
    q_prime = "select ?x where " \
              "{ ?x <http://example.org/prime_minister_of>" + country + " ." \
                                                                        "}"
    if flag == 1:
        ans = g.query(q_president)
    else:
        ans = g.query(q_prime)

    return fix_ans(ans,0)


"""  Main  """

if len(sys.argv) == 1:
    print("Wrong number of arguments")
    exit()
if sys.argv[1] == "create":
    create()
    exit()
if sys.argv[1] == "question":
    if len(sys.argv) != 3:
        print("Wrong number of arguments for question mode")
        exit()
    else:
        g = rdflib.Graph()
        g.parse("ontology.nt", format="nt")
        ans = question(sys.argv[2])
        print(ans)
        exit()
else:
    print("Wrong argument")
    exit()
