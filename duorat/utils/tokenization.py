import abc
from functools import lru_cache
from typing import Dict, List, Sequence, Tuple

import stanza
from transformers import BertTokenizerFast, XLMRobertaTokenizer
from transformers import AutoTokenizer, AutoModelForMaskedLM

# from duorat.utils import registry, corenlp
from duorat.utils import registry


class AbstractTokenizer(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def tokenize(self, s: str, *args, **kwargs) -> List[str]:
        pass

    @abc.abstractmethod
    def detokenize(self, xs: Sequence[str], *args, **kwargs) -> str:
        pass


@registry.register("tokenizer", "StanzaTokenizer")
class StanzaTokenizer(AbstractTokenizer):
    def __init__(self, langs: List[str] = ['en']):
        self.nlp: Dict[str, stanza.Document] = \
            {lang: stanza.Pipeline(lang=lang, processors="tokenize,lemma", logging_level='FATAL', download_method=None) for lang in langs}

    @lru_cache(maxsize=1024)
    def tokenize(self, s: str, lang: str = 'en') -> List[str]:
        doc = self.nlp[lang](s)
        return [
            token.text for sentence in doc.sentences for token in sentence.tokens
        ]

    def tokenize_with_raw(self, s: str, lang='en') -> List[Tuple[str, str]]:
        return [(token.lower(), token) for token in self.tokenize(s, lang)]

    @lru_cache(maxsize=1024)
    def lemma(self, s: str, lang: str = 'en') -> List[str]:
        doc = self.nlp[lang](s)
        return [
            token.lemma for sentence in doc.sentences for token in sentence.words
        ]

    def lemma_with_raw(self, s: str, lang='en') -> List[Tuple[str, str]]:
        return [(token.lower(), token) for token in self.lemma(s, lang)]

    def detokenize(self, xs: Sequence[str], lang: str = 'en') -> str:
        if lang in ['zh', 'ja']:
            return "".join(xs)
        else:
            return " ".join(xs)
            

@registry.register("tokenizer", "BERTTokenizer")
class BERTTokenizer(AbstractTokenizer):
    def __init__(self, pretrained_model_name_or_path: str):
        self._bert_tokenizer = BertTokenizerFast.from_pretrained(
            pretrained_model_name_or_path=pretrained_model_name_or_path
        )

    def tokenize(self, s: str) -> List[str]:
        return self._bert_tokenizer.tokenize(s)

    def tokenize_with_raw(self, s: str) -> List[Tuple[str, str]]:
        # TODO: at some point, hopefully, transformers API will be mature enough
        # to do this in 1 call instead of 2
        tokens = self._bert_tokenizer.tokenize(s)
        encoding_result = self._bert_tokenizer(s, return_offsets_mapping=True)
        assert len(encoding_result[0]) == len(tokens) + 2
        raw_token_strings = [
            s[start:end] for start, end in encoding_result["offset_mapping"][1:-1]
        ]
        raw_token_strings_with_sharps = []
        for token, raw_token in zip(tokens, raw_token_strings):
            # if 'multi' not in self._bert_tokenizer.init_kwargs['vocab_file']:#multilingual-bert-cased
            #     assert (
            #         token == raw_token.lower()
            #         or token[2:] == raw_token.lower()
            #         or token[-2:] == raw_token.lower()
            #     )
            if token.startswith("##"):
                raw_token_strings_with_sharps.append("##" + raw_token)
            elif token.endswith("##"):
                raw_token_strings_with_sharps.append(raw_token + "##")
            else:
                raw_token_strings_with_sharps.append(raw_token)
        return zip(tokens, raw_token_strings_with_sharps)

    def detokenize(self, xs: Sequence[str]) -> str:
        """Naive implementation, see https://github.com/huggingface/transformers/issues/36"""
        text = " ".join([x for x in xs])
        fine_text = text.replace(" ##", "")
        return fine_text

    def convert_token_to_id(self, s: str) -> int:
        return self._bert_tokenizer.convert_tokens_to_ids(s)

    @property
    def cls_token(self) -> str:
        return self._bert_tokenizer.cls_token

    @property
    def sep_token(self) -> str:
        return self._bert_tokenizer.sep_token


@registry.register("tokenizer", "GRAPPATokenizer")
class GRAPPATokenizer(AbstractTokenizer):
    def __init__(self, pretrained_model_name_or_path: str):
        self._bert_tokenizer = AutoTokenizer.from_pretrained(
            use_fast=True,
            pretrained_model_name_or_path=pretrained_model_name_or_path)

    def tokenize(self, s: str) -> List[str]:
        return self._bert_tokenizer.tokenize(s)

    def tokenize_with_raw(self, s: str) -> List[Tuple[str, str]]:
        # TODO: at some point, hopefully, transformers API will be mature enough
        # to do this in 1 call instead of 2
        tokens = self._bert_tokenizer.tokenize(s)
        encoding_result = self._bert_tokenizer(s, return_offsets_mapping=True)
        assert len(encoding_result[0]) == len(tokens) + 2
        raw_token_strings = [
            s[start:end] for start, end in encoding_result["offset_mapping"][1:-1]
        ]
        raw_token_strings_with_sharps = []
        for token, raw_token in zip(tokens, raw_token_strings):
            # assert (
            #     token == raw_token.lower()
            #     or token[2:] == raw_token.lower()
            #     or token[-2:] == raw_token.lower()
            # )
            # if token.startswith("##"):
            #     raw_token_strings_with_sharps.append("##" + raw_token)
            # elif token.endswith("##"):
            #     raw_token_strings_with_sharps.append(raw_token + "##")
            # else:
            raw_token_strings_with_sharps.append(raw_token)
        return zip(tokens, raw_token_strings_with_sharps)

    def detokenize(self, xs: Sequence[str]) -> str:
        """Naive implementation, see https://github.com/huggingface/transformers/issues/36"""
        text = "".join([x for x in xs])
        fine_text = text.replace("Ġ", " ")
        return fine_text

    def convert_token_to_id(self, s: str) -> int:
        return self._bert_tokenizer.convert_tokens_to_ids(s)

    @property
    def cls_token(self) -> str:
        return self._bert_tokenizer.cls_token

    @property
    def sep_token(self) -> str:
        return self._bert_tokenizer.sep_token


@registry.register("tokenizer", "XLMRTokenizer")
class XLMRTokenizer(AbstractTokenizer):
    def __init__(self, pretrained_model_name_or_path: str):
        self._bert_tokenizer = AutoTokenizer.from_pretrained(
            use_fast=True,
            pretrained_model_name_or_path=pretrained_model_name_or_path)

    def tokenize(self, s: str) -> List[str]:
        return self._bert_tokenizer.tokenize(s)

    def tokenize_with_raw(self, s: str) -> List[Tuple[str, str]]:
        # TODO: at some point, hopefully, transformers API will be mature enough
        # to do this in 1 call instead of 2
        tokens = self._bert_tokenizer.tokenize(s)
        encoding_result = self._bert_tokenizer(s, return_offsets_mapping=True)
        assert len(encoding_result[0]) == len(tokens) + 2
        raw_token_strings = [
            s[start:end] for start, end in encoding_result["offset_mapping"][1:-1]
        ]
        raw_token_strings_with_sharps = []
        for token, raw_token in zip(tokens, raw_token_strings):
            raw_token_strings_with_sharps.append(raw_token)
        return zip(tokens, raw_token_strings_with_sharps)

    def detokenize(self, xs: Sequence[str]) -> str:
        """Naive implementation, see https://github.com/huggingface/transformers/issues/36"""
        text = "".join([x for x in xs])
        fine_text = text.replace("\u2581", " ")
        # if fine_text[0] == "\u2581":
        #     fine_text = fine_text[1:]
        return fine_text

    def convert_token_to_id(self, s: str) -> int:
        return self._bert_tokenizer.convert_tokens_to_ids(s)

    @property
    def cls_token(self) -> str:
        return self._bert_tokenizer.cls_token

    @property
    def sep_token(self) -> str:
        return self._bert_tokenizer.sep_token