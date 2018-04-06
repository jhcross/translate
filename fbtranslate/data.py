#!/usr/bin/env python3

import os

from fairseq import data, indexed_dataset
from typing import NamedTuple, Optional, Tuple

from language_technology.neural_mt.fbtranslate import dictionary as \
    fbtranslate_dictionary


class CorpusConfig(NamedTuple):
    dialect: str
    data_file: str
    vocab_file: Optional[str]
    # max_vocab_size < 0 means no max vocab size.
    max_vocab_size: int


class ParallelCorpusConfig(NamedTuple):
    source: CorpusConfig
    target: CorpusConfig


def _gen_corpus_config(data_dir, source_lang, target_lang, split):
    return ParallelCorpusConfig(
        source=CorpusConfig(
            dialect=source_lang,
            data_file=os.path.join(data_dir, f'{split}.{source_lang}'),
            vocab_file=None,
            max_vocab_size=-1,
        ),
        target=CorpusConfig(
            dialect=target_lang,
            data_file=os.path.join(data_dir, f'{split}.{target_lang}'),
            vocab_file=None,
            max_vocab_size=-1,
        ),
    )


def infer_file_paths(
    data_dir: str,
    source_lang: str,
    target_lang: str,
    train_split: str,
    eval_split: str,
) -> Tuple[ParallelCorpusConfig, ParallelCorpusConfig]:
    train_corpus, eval_corpus = [
        _gen_corpus_config(
            data_dir=data_dir,
            source_lang=source_lang,
            target_lang=target_lang,
            split=split,
        ) for split in [train_split, eval_split]
    ]
    return train_corpus, eval_corpus


def _get_dictionary(corpus: CorpusConfig, save_dir: str, tokens_with_penalty=None):
    vocab_file = corpus.vocab_file
    if not vocab_file:
        vocab_file = os.path.join(save_dir, f'dictionary-{corpus.dialect}.txt')

    if os.path.isfile(vocab_file):
        try:
            d = fbtranslate_dictionary.Dictionary.load(vocab_file)
            print(
                f'Re-using existing vocab file {vocab_file}. '
                'Ignoring any specified max vocab size.'
            )
            return d
        except Exception as e:
            print(
                f'Failed to re-use existing vocab file {vocab_file} '
                f'due to exception {e}. Overwriting the file with new vocab.'
            )
    else:
        print(f'Generating new vocab to be saved at {vocab_file}.')

    d = fbtranslate_dictionary.Dictionary()
    with open(corpus.data_file, 'r') as f:
        for line in f:
            tokens = line.split()
            for t in tokens:
                token_index = d.add_symbol(t)

    # Set indices to receive penalty
    if tokens_with_penalty:
        # Assume input tokens are unique
        bad_words_list = []
        with open(tokens_with_penalty, 'r', encoding='utf-8') as f:
            for line in f:
                tokens = line.strip().split()
                if len(tokens) == 1:
                    bad_words_list.append(tokens[0])

        for token, token_index in d.indices.items():
            if token in bad_words_list:
                d.profanity_indices.add(token_index)

    d.finalize()
    # Save and re-load the dictionary to enforce max vocab size, since the
    # pruning is only done when saving the vocab file.
    d.save(vocab_file, threshold=0, nwords=corpus.max_vocab_size)
    d = fbtranslate_dictionary.Dictionary.load(vocab_file)
    return d


def load_raw_text_dataset(
    train_corpus: ParallelCorpusConfig,
    eval_corpus: ParallelCorpusConfig,
    train_split: str,
    eval_split: str,
    save_dir: str,
    penalized_target_tokens_file=None,
    append_eos_to_source=False,
    reverse_source=False,
) -> data.LanguageDatasets:
    # TODO: Replace this with our new VocabProcessor once it's ready
    source_dict = _get_dictionary(
        corpus=train_corpus.source,
        save_dir=save_dir,
    )
    target_dict = _get_dictionary(
        corpus=train_corpus.target,
        save_dir=save_dir,
        tokens_with_penalty=penalized_target_tokens_file,
    )

    dataset = data.LanguageDatasets(
        src=train_corpus.source.dialect,
        dst=train_corpus.target.dialect,
        src_dict=source_dict,
        dst_dict=target_dict,
    )

    prev_source_dialect = None
    prev_target_dialect = None

    for split, corpus in [
        (train_split, train_corpus),
        (eval_split, eval_corpus),
    ]:
        # Sanity check that all language directions are consistent until this
        # has been updated to support multilingual corpora.
        if prev_source_dialect is None and prev_target_dialect is None:
            prev_source_dialect = corpus.source.dialect
            prev_target_dialect = corpus.target.dialect
        elif (prev_source_dialect != corpus.source.dialect or
                prev_target_dialect != corpus.target.dialect):
            raise ValueError(
                'We currently only support monolingual directions - expected '
                '{}->{} for all corpora, but found {}->{} for split {}'.format(
                    prev_source_dialect,
                    prev_target_dialect,
                    corpus.source.dialect,
                    corpus.target.dialect,
                    split,
                )
            )

        dataset.splits[split] = data.LanguagePairDataset(
            src=indexed_dataset.IndexedRawTextDataset(
                path=corpus.source.data_file,
                dictionary=source_dict,
                append_eos=append_eos_to_source,
                reverse_order=reverse_source,
            ),
            dst=indexed_dataset.IndexedRawTextDataset(
                path=corpus.target.data_file,
                dictionary=target_dict,
                append_eos=True,
                reverse_order=False,
            ),
            pad_idx=dataset.src_dict.pad(),
            eos_idx=dataset.src_dict.eos(),
        )

    return dataset