import logging
from pprint import pprint
from textx.exceptions import TextXError
from textx.metamodel import metamodel_from_file
from textx.metamodel import metamodel_from_str


class Grammar(object):
    def __init__(self):
        self.logger = logging.getLogger(type(self).__name__)

    @classmethod
    def from_string(cls, grammar_definition):
        return cls()._create_meta_model_from_string(grammar_definition)

    @classmethod
    def from_file(cls, grammar_file):
        return cls()._create_meta_model_from_file(grammar_file)

    def _create_meta_model_from_string(self, definition):
        try:
            self._mm = metamodel_from_str(definition)
            pprint(self._mm, indent=4)
        except TextXError as e:
            self.logger.error('Error creating meta-model from string: %s -> (line: %s, col: %s)', e.message, e.line,
                              e.col)
        else:
            return self

    def _create_meta_model_from_file(self, filename):
        try:
            self._mm = metamodel_from_file(filename)
            pprint(self._mm, indent=4)
        except TextXError as e:
            self.logger.error('Error creating meta-model from file: %s -> (line: %s, col: %s)', e.message, e.line,
                              e.col)
        else:
            return self

    def parse_from_string(self, input_string, debug=None):
        """
        A model is created from the input string. In a sense this structure is an Abstract Syntax Tree (AST) known
        from the classic parsing theory, but is actually a graph structure where each reference is resolved to a
        proper python reference. Each object is an instance of a class from the meta-model. Classes are created on
        the fly from the grammar rules.
        """
        if not debug:
            self.logger.setLevel(logging.CRITICAL)
        try:
            return self._mm.model_from_str(input_string, debug=debug)
        except TextXError as e:
            self.logger.error('Error creating model from file: %s -> (line: %s, col: %s)', e.args, e.line, e.col)
            raise e
        finally:
            self.logger.setLevel(logging.INFO)

    def parse_from_file(self, input_file, debug=None):
        """
        A model is created from the given file. In a sense this structure is an Abstract Syntax Tree (AST) known
        from the classic parsing theory, but is actually a graph structure where each reference is resolved to a
        proper python reference. Each object is an instance of a class from the meta-model. Classes are created on
        the fly from the grammar rules.
        """
        if not debug:
            self.logger.setLevel(logging.CRITICAL)
        try:
            return self._mm.model_from_file(input_file, encoding='utf-8', debug=debug)
        except TextXError as e:
            self.logger.error('Error creating model from file: %s -> (line: %s, col: %s)', e.args, e.line, e.col)
            raise e
        finally:
            self.logger.setLevel(logging.INFO)

    def register_obj_processor(self, processor):
        self._mm.register_obj_processors(processor)

    def register_model_processor(self, processor):
        self._mm.register_model_processor(processor)
