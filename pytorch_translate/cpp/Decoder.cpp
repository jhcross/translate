/*
Sample decoder to load an exported Caffe2 model and perform
inference/beam search to provide translation results.

Sample usage (assuming that cmake has already been run as a part of the
installation done by install.sh and that you're in the cpp directory):
  make && \
  echo "sentence to translate" | \
  ./translation_decoder \
    --encoder_model "/path/to/exported/encoder" \
    --decoder_step_model "/path/to/exported/decoder" \
    --source_vocab_path "/path/to/source_vocab.txt" \
    --target_vocab_path "/path/to/target_vocab.txt" \
    `# Tuneable parameters` \
    --beam_size 6 \
    --max_out_seq_len_mult 1.1 \
    --max_out_seq_len_bias 5 \
    `# Must match your training settings` \
    --reverse_source True \
    --append_eos_to_source False \
    `# Unset for more logging/debug messages` \
    --caffe2_log_level 3
*/

#include <cstdio>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>

#include <caffe2/core/flags.h>
#include <caffe2/core/init.h>

#include "DecoderLib.h"

namespace pyt = pytorch::translate;

CAFFE2_DEFINE_string(encoder_model, "", "Encoder model path");
CAFFE2_DEFINE_string(decoder_step_model, "", "Decoder step model path");
CAFFE2_DEFINE_string(source_vocab_path, "", "Source vocab file");
CAFFE2_DEFINE_string(target_vocab_path, "", "Target vocab file");

CAFFE2_DEFINE_int(beam_size, -1, "Beam size");
CAFFE2_DEFINE_double(
    max_out_seq_len_mult, -1,
    "Determines max num tokens in translation based on num tokens in input"
    "max_out_tokens = "
    "input_tokens * max_out_seq_len_mult + max_out_seq_len_bias");
CAFFE2_DEFINE_int(
    max_out_seq_len_bias, -1,
    "Determines max num tokens in translation based on num tokens in input"
    "max_out_tokens = "
    "input_tokens * max_out_seq_len_mult + max_out_seq_len_bias");

CAFFE2_DEFINE_bool(reverse_source, true,
                   "Whether to reverse source sentence before encoding");
CAFFE2_DEFINE_bool(
    stop_at_eos, true,
    "If true, do not consider sequences containing a non-final EOS token");
CAFFE2_DEFINE_bool(append_eos_to_source, false,
                   "Whether to aqppend EOS token to source sentence.");
CAFFE2_DEFINE_double(
    length_penalty, 0,
    "Hypothesis score is divided by (numwords ^ length_penalty)");

int main(int argc, char** argv) {
  // Sets up command line flag parsing, etc.
  caffe2::GlobalInit(&argc, &argv);

  if (caffe2::FLAGS_source_vocab_path.empty() ||
      caffe2::FLAGS_target_vocab_path.empty() ||
      caffe2::FLAGS_encoder_model.empty() ||
      caffe2::FLAGS_decoder_step_model.empty()) {
    LOG(FATAL)
        << "Error: --source_vocab_path, --target_vocab_path, "
        << "--encoder_model, and --decoder_step_model must all be defined. "
        << "(source_vocab_path='" << caffe2::FLAGS_source_vocab_path
        << "', target_vocab_path='" << caffe2::FLAGS_target_vocab_path
        << "', encoder_model='" << caffe2::FLAGS_encoder_model
        << "', decoder_step_model='" << caffe2::FLAGS_decoder_step_model
        << "')";
  }

  std::shared_ptr<pyt::Dictionary> sourceVocab =
      std::make_shared<pyt::Dictionary>(caffe2::FLAGS_source_vocab_path);
  std::shared_ptr<pyt::Dictionary> targetVocab =
      std::make_shared<pyt::Dictionary>(caffe2::FLAGS_target_vocab_path);
  std::shared_ptr<pyt::NmtDecoder> decoder = std::make_shared<pyt::NmtDecoder>(
      caffe2::FLAGS_beam_size, caffe2::FLAGS_max_out_seq_len_mult,
      caffe2::FLAGS_max_out_seq_len_bias, std::move(sourceVocab),
      std::move(targetVocab), caffe2::FLAGS_encoder_model,
      caffe2::FLAGS_decoder_step_model, caffe2::FLAGS_reverse_source,
      caffe2::FLAGS_stop_at_eos, caffe2::FLAGS_append_eos_to_source,
      caffe2::FLAGS_length_penalty);

  if (decoder == nullptr) {
    LOG(FATAL) << "failed to load decoder";
  }

  LOG(INFO) << "Ready to translate";

  for (std::string line; std::getline(std::cin, line);) {
    pyt::TranslationResult translationResult;
    translationResult = decoder->translate(line);
    std::cout << translationResult.translation << "\n";
  }
}
