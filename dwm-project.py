import requests
import lxml.html
import rdflib
import sys
import re

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
                        "Maeen Abdulmalik Saeed": "1976", "Mohamed Béavogui": "15-08-1953"}
PROBLEMATIC_BIRTHPLACE = {'Hasan Akhund': "Pashmul", "Rashad al-Alimi": "Al-Aloom", 'Moustafa Madbouly': "",
                          'Myint Swe': "", "Maeen Abdulmalik Saeed": "Ta'izz", "Mohamed Béavogui": "Porédaka",
                          'Ariel Henry': "", 'Bisher Al-Khasawneh': ""}
PROBLEMATIC_AREA = {"Israel": "20770/22072"}
PROBLEMATIC_PRESIDENT = {"Yemen": "Rashad al-Alimi"}
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


def get_personal_info(name):
    if name in PROBLEMATIC_NAME:
        res = get_wiki_url(PROBLEMATIC_NAME[name])
    else:
        res = get_wiki_url(name)
    doc = lxml.html.fromstring(res.content)
    info_box = doc.xpath("//table[contains(@class, 'infobox')]")
    if not info_box:
        return {"Name": fixing_prefix(name), "POB": fixing_prefix(""), "DOB": fixing_prefix("")}
    born = info_box[0].xpath("//table//th[contains(text(), 'Born')]")
    try:
        dob = PROBLEMATIC_BIRTHDAY[name] if name in PROBLEMATIC_BIRTHDAY else born[0].xpath("./../td//span["
                                                                                        "@class='bday']//text("
                                                                                        ")")[0].replace(" ", "_")
    except IndexError:
        born_text = born[0].xpath("./../td//text()")
        dob = next(line for line in born_text if re.compile("[0-9]+").search(line))
        dob = dob.replace(" ", "_")
    try:
        pob = PROBLEMATIC_BIRTHPLACE[name] if name in PROBLEMATIC_BIRTHPLACE else born[0].xpath("./../td//a/text()")[0]
    except IndexError:
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
        answer = " ".join(gov_clean)
        res.append(fixing_prefix(answer))
    except IndexError:
        res.append(fixing_prefix(""))
    return res


def get_president(info_box, country_name):
    res = []
    if country_name in PROBLEMATIC_PRESIDENT:
        res.append(fixing_prefix(PROBLEMATIC_PRESIDENT[country_name]))
    else:
        try:
            president = info_box[0].xpath("(//tbody/tr[./descendant::a[contains(text(), 'President')]])[1]/td/*[1]/text()")
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
        area_final = area_final.replace('(', '').replace(')', '').replace("'", '')
        if "km" not in area_final:
            area_final += " km"
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
    #print("Getting info for: " + name)
    return {
        "President": get_president(info_box, name),
        "Prime Minister": get_pm(info_box),
        "Population": get_population(info_box, name),
        "Area": get_area(info_box, name),
        "Government Type": get_government_type(info_box, name),
        "Capital": get_capital(info_box, name)
    }


def create():
    g = rdflib.Graph()
    for country in get_list_of_countries():
        info = get_country_info(country)
        for field in info.keys():
            if info[field]:
                if field == "President" or field == "Prime Minister":
                    person_name = remove_prefix(info[field][0])
                    if person_name != '':
                        personal_details = get_personal_info(person_name)
                        g.add((info[field][0], fixing_prefix("pob"), personal_details["POB"]))
                        g.add((info[field][0], fixing_prefix("dob"), personal_details["DOB"]))
                if not info[field]:
                    g.add((fixing_prefix(country), fixing_prefix(field), fixing_prefix('')))
                else:
                    g.add((fixing_prefix(country), fixing_prefix(field), fixing_prefix(info[field][0])))
        #print("Done with country: " + country)
    g.serialize("ontology.nt", format="nt", encoding="utf-8")
    sys.exit()


# Part two - question
def question():
    q = sys.argv[2].replace(" ", "_")
    graph = rdflib.Graph()
    graph.parse("ontology.nt", format="nt")
    sys.exit()

create()

# Main
# if (sys.argv[1] == "create"):
#    create()
# if (sys.argv[1] == "question"):
#    question()
