"""
Format reddit data for GTT
"""

import json
from collections import OrderedDict
from pprint import pprint
from reader import read_docs

#TEMPLATES: start is in between (start_min,  start_max) exclusive UNLESS 
#			start_min == start_max, then start = those values
def generate_examples(data):
	examples = []

	for doc in data:
		ex = OrderedDict([("docid", doc.doc_id), ("doctext", None), ("templates", None)])

		# Preprocess text
		## Calculate character left-shift
		start_string = "0000-00-00"
		text = f"Story begins: {start_string}. Story ends: {doc.dct}."
		start_entity = [[start_string, text.find(start_string)]]
		dct_entity = [[doc.dct, text.find(doc.dct)]]
		if doc.dct == start_string:
			print(f"Error: {doc.id} has faulty DCT {doc.dct}")
			continue
		
		if len(doc.title.strip()) > 0:
			title_shift = len(text) - (len(doc.title) - len(doc.title.lstrip())) + 1
			text += "\n" + doc.title.strip()
		body_shift = len(text) -(len(doc.body) - len(doc.body.lstrip())) + 1
		text += "\n" + doc.body.strip()
		text = text.lower()
		ex["doctext"] = text

		def create_role_filler(entities):
			role = []
			# if date_id == "DCT": # Special case: DCT
			# 	role = [[doc.dct, -1]]
			# 	continue

			for ent in entities:#doc.dates[date_id]:
				span_index =  ent.span[0]
				if ent.source == 0:
					span_index += title_shift
				else:
					span_index += body_shift
				role.append([ent.string, span_index])
			return role

		ex["templates"] = []
		# Add template for each medication
		for med_id, med_mentions in doc.meds.items():
			if doc.labels[med_id]["DCT"] == "before":
				#invalid label
				continue
			template = OrderedDict()
			template["Medication"]  = create_role_filler(med_mentions)

			template["Start_min"] = [start_entity]
			template["Start_max"] = None
			template["Stop_min"] = None
			template["Stop_max"] = None

			# Get labels
			for date_id, label in doc.labels[med_id].items():
				if label == "uncertain":
					continue
				if label == "no_intake":
					break
				if date_id == "DCT":
					role = [dct_entity]
				else:
					role = create_role_filler(doc.dates[date_id])

				if label == "before":
					template["Start_min"] = role
					template["Stop_min"] = role
				elif not template["Start_max"]:
						template["Start_max"] = role
				if label == "start":
					template["Start_min"] = role
					template["Start_max"] = role
					template["Stop_min"] = role
				if label == "on":
					template["Stop_min"] = role
				if label == "stop":
					template["Stop_min"] = role
					template["Stop_max"] = role
				if label == "after":
					if not template["Stop_max"]:
						template["Stop_max"] = role

			if template["Stop_min"] and not template["Stop_max"]:
				# If never stopped (e.g. no after or stop label), the remove stop_min
				template["Stop_min"] = None

			#TODO get durations

			# Add med-template if pos_intake and at least one non-uncertain relation 
			if template["Start_max"]: 
				ex["templates"].append(template)

		if len(ex["templates"]) > 0:
			examples.append(ex)

	return examples

if __name__=='__main__':

	data_path = "/Users/Barbara_1/Desktop/research/RedditBPTimelines/rMINT_Refactor/data/labelled_data.json"

	data = read_docs(data_path)
	examples = generate_examples(data)
	print(len(examples))
