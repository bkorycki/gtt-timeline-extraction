import json
from itertools import groupby
from typing import List

def read_docs(fpath, num_docs: int = None, doc_ids: list = None) -> list:
	'''
	Returns list of Document objects
	'''	
	with open(fpath, 'r', encoding='utf-8') as json_rf:
		data = json.load(json_rf, object_hook=DataDecoder)

	if doc_ids:
		new_docs = []
		for doc in data:
			if len(new_docs) == len(doc_ids):
				break
			if doc.doc_id in doc_ids:
				new_docs.append(doc)
		data = new_docs
	if num_docs:
		data = data[:num_docs]
	return data


class DataEncoder(json.JSONEncoder):
	def default(self, obj):
		if hasattr(obj, 'to_json'):
			return obj.to_json()
		return obj.__dict__

def DataDecoder(obj):
	if "doc_id" in obj:
		return Document(**obj)
		# return Document.from_json(obj)
	elif "entity_id" in obj:
		return Entity(**obj)
		# return Entity.from_json(obj)x
	return obj

	
class Document:
	__NAN_VALUE	= ""

	def __init__(self, doc_id: str, title: str, body: str,
				 dct, author: str, subreddit: str,
				 meds: list, dates=[], durs=[], labels =None):
		assert(len(meds) > 0)
		
		self.doc_id 	= doc_id
		self.title 		= title
		self.body 		= body

		self.author 	= author
		self.subreddit 	= subreddit

		self.meds 			= self.process_entities(meds)
		self.dct 			= dct
		self.dates 			= self.process_entities(dates)
		self.durs			= self.process_entities(durs)

		self.labels = labels # {med_id:    {"data_id": label, ..}}

		self._clean_text()	
		self._validate()

	def _clean_text(self):
		if len(self.title) == 0 and len(self.body) == 0:
			raise Exception("Invalid document (both title and body are empty)")

		self.title = self.preprocess_text(self.title)		
		self.body = self.preprocess_text(self.body)	
		return 

	@staticmethod
	def preprocess_text(text):
		if len(text) == 0:
			text = Document.__NAN_VALUE
		return text

	def process_entities(self, entities):
		if type(entities) == dict:
			return entities
		if type(entities) == list:
			return self.group_entities(entities)
		else:
			raise Exception("Entities must be provided as list or dict.")

	@staticmethod
	def group_entities(mentions: List):
		"""
		Creates a dict. mapping entity_ids to a list of mentions (entity objects)
		Assigns "mention_id" to entity objects based on order of appearance
		mention_list: list of Entity objects
		"""
		if len(mentions) == 0:
			return {}
		
		# group by entity_id: list of lists
		mentions.sort(key=lambda e: e.entity_id)
		groups = groupby(mentions, lambda e: e.entity_id)

		entities = {}
		for ent_id, group in groups:
			# sort by order of appearance
			group = sorted(list(group), key=lambda e: (e.source, e.span[0]))
			# Assign mention_ids
			for mention_id, mention in enumerate(group):
				mention.mention_id = f"mention_{mention_id}"
			entities[ent_id] = group

		return entities
			
		
	def _get_typed_entities(self):
		return [("med", self.meds), ("date", self.dates), ("dur", self.durs)]

	def _validate(self):
		if len(self.meds) == 0:
			raise Exception("Error: medication list cannot be empty.")		

		for ent_type, entities in self._get_typed_entities():
			for ent_id, mentions in entities.items():
				if any(e.type!=ent_type for e in mentions):
					raise Exception(f"Invalid entities: need to be of type {ent_type}")
				if any(e.entity_id != ent_id for e in mentions):
					raise Exception("Misaligned entities")
				if len(set([e.mention_id for e in mentions])) != len(mentions):
					raise Exception("Non-unique mention ids")

	@classmethod
	def from_json(cls, j):
		return cls(**j)

	def to_json(self):
		if self.labels:
			return self.__dict__
		# don't include labels attribute if empty
		return {key: self.__dict__[key] for key in self.__dict__.keys() if key != "labels"}

	def __str__(self):
		return json.dumps(self.__dict__, ensure_ascii=False, indent=True, cls=DataEncoder)
		

class Entity:
	def __init__(self, type: str, entity_id: str, source: int, span: tuple, string, mention_id: str=None, info: dict=None, **kwargs):
		self.type 		= type.lower() # med, date, dur
		self.entity_id  = entity_id
		self.source		= source # 0 for title, 1 for body
		self.span		= span # character span
		self.string		= string
		self.mention_id = mention_id
		self.info = info

		if len(kwargs) > 0:
			if not self.info:
				self.info = {}
			self.info.update(kwargs)

		self._validate()

	def _validate(self):
		# Valid type
		if self.type not in ["med", "date", "dur"]:
			raise Exception(f"Invalid entity type {self.type}")
		# Non-empty string
		if len(self.string) == 0: 
			raise Exception("Invalid string value")
		# Valid source
		if self.source not in [0,1]:
			raise Exception(f"Invalid source {self.source}: must be 0 (title) or 1 (body)")
		# Valid span
		a, b = self.span
		if a<0 or b<0 or a >= b or len(self.string) != b-a:
			raise Exception(f"Invalid span {self.span}")	

	def to_json(self):
		json_ent = self.__dict__.items()
		return {k: v for k, v in json_ent if v is not None} # Exclude 'None' items

	def __str__(self):
		return str(self.to_json())