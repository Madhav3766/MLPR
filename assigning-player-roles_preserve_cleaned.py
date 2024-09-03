import requests

from bs4 import BeautifulSoup

import csv



with open('/Users/hemantg/Desktop/players-espn-codes.csv', 'r') as file:

    reader = csv.reader(file)

    data = list(reader)



header = data[0]

rows = data[1:]



output_data = []


for row in rows:

    name = row[0]

    key_cricinfo = row[1]



    url = f"https://www.espncricinfo.com/cricketers/hi-hello-{key_cricinfo}"



    response = requests.get(url)

    html_content = response.content



    soup = BeautifulSoup(html_content, "html.parser")



    playing_role_tag = soup.find("p", string="Playing Role")



    if playing_role_tag:


        span_tag = playing_role_tag.find_next_sibling("span")



        if span_tag:


            role_text = span_tag.find("p").get_text(strip=True)

            output_data.append([name, key_cricinfo, role_text])

        else:

            output_data.append([name, key_cricinfo, ''])

    else:

        output_data.append([name, key_cricinfo, ''])



with open('/Users/hemantg/Desktop/player-espn-roles.csv', 'w', newline='') as file:

    writer = csv.writer(file)

    writer.writerow(['name', 'key_cricinfo', 'span-tag-text'])

    writer.writerows(output_data)



with open('/Users/hemantg/Desktop/player-espn-roles.csv', 'r') as infile:

    reader = csv.DictReader(infile)

    data = list(reader)



def get_role(span_tag_text):

    span_tag_text = span_tag_text.lower()

    if 'wicket' in span_tag_text:

        return 'WK'

    elif 'all' in span_tag_text:

        return 'AR'

    elif 'bowl' in span_tag_text:

        return 'BWL'

    elif 'bat' in span_tag_text:

        return 'BAT'

    else:

        return ''



for row in data:

    span_tag_text = row['span-tag-text']

    role = get_role(span_tag_text)

    row['role'] = role


any_role_assigned = any(row['role'] for row in data)



with open('/Users/hemantg/Desktop/coded-roles-output.csv', 'w', newline='') as outfile:

    fieldnames = ['name', 'key_cricinfo', 'span-tag-text', 'role']

    writer = csv.DictWriter(outfile, fieldnames=fieldnames)

    writer.writeheader()


    if any_role_assigned:

        writer.writerows(data)

    else:

        print("No roles were assigned. The output CSV file will be empty.")
