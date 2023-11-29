"""
Format reddit data for GTT
TEMPLATES: 
	Each value is a list of entity mentions as (string, char_offset) tuples
	Start is in between (Start_min,  Start_max) exclusive 
	 UNLESS  Start_min == Start_max, then start = those values

"""

import json
from collections import OrderedDict
from typing import List, Tuple
 
from pprint import pprint
from reader import read_docs


MIN_DATE_STRING  = "0000-00-00"

def format_text(doc) -> (str, int, int):
	"""
	Formats text by concatenating title + body, stripping whitespace, and lower casing.
	Injects DCT entity and dummy MIN_date entity.
	Calculates resulting character shift for entities originating in the title and body.
	Returns: text, title shift, body shift
	"""
	if doc.dct == MIN_DATE_STRING:
		print(f"Error: {doc.doc_id} has faulty DCT {doc.dct}")
		return 
	
	text = f"Story begins: {MIN_DATE_STRING}. Story ends: {doc.dct}."
	if len(doc.title.strip()) > 0:
		title_shift = len(text) - (len(doc.title) - len(doc.title.lstrip())) + 1
		text += "\n" + doc.title.strip()
	body_shift = len(text) -(len(doc.body) - len(doc.body.lstrip())) + 1
	text += "\n" + doc.body.strip()
	text = text.lower()

	return text, (title_shift, body_shift)

def format_entity_mentions(mentions: List, title_shift: int, body_shift: int) ->  List[Tuple[str, int]]:
	"""
	Formats list of entity-mentions for TLTemplate attributes 
	and updates character offsets
	"""
	formatted = []
	for ment in mentions:
		offset =  ment.span[0]
		if ment.source == 0:
			offset += title_shift
		else:
			offset += body_shift
		formatted.append([ment.string, offset])
	return formatted

def format_example(doc):
	example = OrderedDict([("docid", doc.doc_id), ("doctext", None), ("templates", [])])

	text, shifts= format_text(doc)
	example["doctext"] = text

	# Format date entities
	MIN_entity = [MIN_DATE_STRING, text.find(MIN_DATE_STRING)]
	DCT_entity = [doc.dct, text.find(doc.dct)]
	# Chronological map: date_id -> formatted entity
	date_entities = OrderedDict([(date_id, format_entity_mentions(doc.dates[date_id], *shifts)) for date_id in doc.dates])
	date_entities["DCT"] = [DCT_entity]

	# Add template for each medication
	for med_id, med_mentions in doc.meds.items():
		if doc.labels[med_id]["DCT"] == "before":
			# Invalid label
			continue

		template = OrderedDict([("Medication", []), ("Start_min", [MIN_entity]), ("Start_max", None), ("Stop_min", [MIN_entity]), ("Stop_max", None)])
		template["Medication"] = format_entity_mentions(med_mentions, *shifts)

		# Get labels (order: before, start, on, stop, after)
		for date_id, date_mentions in date_entities.items():
			label = doc.labels[med_id][date_id]
			if label == "uncertain":
				continue
			if label == "no_intake":# TODO
				break
			
			if label in ["before", "start"]:
				# Update Start MIN. to last label <= start
				template["Start_min"]= date_mentions
			if label != "before" and not template["Start_max"]:
				# Update Start MAX. to first label >= "start"
				template["Start_max"]= date_mentions
			if label != "after":
				# Update Stop MIN. to last label <= "stop"
				template["Stop_min"] = date_mentions
			if label == "stop" or (label == "after" and not template["Stop_max"]):
				# Update Stop MAX. to first label >= "stop"
				template["Stop_max"] = date_mentions

		if  not template["Stop_max"]:
			# Removed Stop_min if never stopped
			template["Stop_min"] = None 
		if template["Start_max"]:
			# Add template if positive_intake and at least one non-uncertain relation
			example["templates"].append(template)

		#TODO get durations
	return example




if __name__=='__main__':

	data_path = "/Users/Barbara_1/Desktop/research/RedditBPTimelines/rMINT_Refactor/data/labelled_data.json"

	data = read_docs(data_path)
	examples = []
	for doc in data:
		ex =  format_example(doc)
		if ex["templates"]:
			# for t in ex["templates"]:
			# 	for ent_list in t.values():
			# 		if ent_list:
			# 			for string, i in ent_list:
			# 				# print(string, ex["doctext"][i:i+len(string)] )
			# 				assert string.lower() == ex["doctext"][i:i+len(string)]
			examples.append(ex)

	# # TODO: split data
	# for div in ["train", "dev", "test"]:

	# Save files
	div = "test"
	processed_file = "processed/" + div + ".json"
	with open(processed_file, "w") as f_processed:
		for ex in examples:
			f_processed.write(json.dumps(ex) + "\n")
	# pretty written
	processed_file = "processed/pretty_" + div + ".json"
	with open(processed_file, "w") as f_processed:
		for ex in examples:
			f_processed.write(json.dumps(ex, indent=4) + "\n")
