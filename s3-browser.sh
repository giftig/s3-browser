#!/bin/bash

set -o vi

CURRENT_PATH=''
HISTORY_FILE="$HOME/.s3_browser_history"
HISTORY_POS=0
HISTORY_CACHE=''
MAX_HISTORY_LINES=10000
PROMPT='s3://$(tput setaf 6)$CURRENT_PATH$(tput sgr0)> '

# STRING AND PATH UTILS
_strip_quotes() {
  echo "$1" | sed -E 's/["'"']//g"
}

_combine_paths() {
  local BASE_PATH="$1"
  local EXTRA_PATH="$2"
  local EXPLICIT_DIR=0
  local p=''

  if [[ "${EXTRA_PATH:0:1}" == '/' ]]; then
    echo "${EXTRA_PATH:1}"
    return 0
  fi

  if [[ "${EXTRA_PATH: -1}" == / ]]; then
    EXPLICIT_DIR=1
  fi

  p="$BASE_PATH/$EXTRA_PATH"

  # Resolve .. expressions and the like
  # TODO: Not portable to mac unless you install GNU readlink
  p="$(readlink -m "/$p")"
  p="${p:1}"

  if [[ "${EXTRA_PATH: -1}" == '/' ]]; then
    p="$p/"
  fi
  echo "$p"
}

# Call aws s3 ls
# TODO: Add some caching
_s3() {
  aws s3 ls "$@"
}

# PROMPT UTILS
# Autocomplete path when hitting TAB on cd or ls commands
_autocomplete_path() {
  local PREFIX="${READLINE_LINE:0:3}"

  if [[ "$PREFIX" != 'ls ' && "$PREFIX" != 'cd ' ]]; then
    return 0
  fi

  local SEARCH_PATH='.'
  local LAST_SEGMENT=''
  local COMPLETION=''

  # We'll try to complete the path by making the current path under cursor
  # absolute and running ls to look for options
  SEARCH_PATH=$(echo "$READLINE_LINE" | cut -d ' ' -f 2)

  if [[ "${SEARCH_PATH:0:1}" == '/' ]]; then
    SEARCH_PATH=/$(_combine_paths "$SEARCH_PATH" '')
  else
    SEARCH_PATH=$(_combine_paths "$CURRENT_PATH" "${SEARCH_PATH:-.}")
  fi

  # If we were mid-word when we hit tab, we need to strip the partial word from
  # the readline segment so that we can replace it with the full suggestion instead
  if [[ "${READLINE_LINE: -1}" != '/' ]]; then
    STRIPPED_LINE="$(echo "$READLINE_LINE" | sed -E 's/[^ \/]+$//')"
  else
    STRIPPED_LINE="$READLINE_LINE"
  fi

  # We need to match only the last part of the search path against our results
  # as the output isn't going to include full paths
  if echo "$SEARCH_PATH" | fgrep / &> /dev/null; then
    LAST_SEGMENT="$(echo "$SEARCH_PATH" | rev | cut -d '/' -f 1 | rev)"
  fi

  # Find relevant subkeys for our word and generate suggestions
  LS_RESULTS=$(_s3 "s3://$SEARCH_PATH" | sed -E 's/^.+ //' | tr '\r\n' ' ')

  COMP_OPTS=($(compgen -W "$LS_RESULTS" "$LAST_SEGMENT"))

  # Take the first suggestion; if there isn't one, we'll leave the partial word segment in place
  COMPLETION="${COMP_OPTS[0]}"
  if [[ "$COMPLETION" == '' ]]; then
    COMPLETION="$LAST_SEGMENT"
  fi

  # Now check if the trailing segment of the path was identical to one of the results
  # If it's identical to the only result, we'll add a slash and assume we want to continue.
  # If there's a subsequent result, we'll cycle forward to that result instead; the idea is
  # they probably just hit tab and got this result but wanted a different one.
  if [[ "$LAST_SEGMENT" == "$LS_RESULTS" ]]; then
    COMPLETION="$LAST_SEGMENT/"
  else
    NEXT_WORD=$(
      echo "$LS_RESULTS$LS_RESULTS" |
        fgrep " $LAST_SEGMENT " |
        sed -E 's/^.*('"$LAST_SEGMENT"') +([^ ]+).*$/\2/'
    )
    if [[ "$NEXT_WORD" != '' ]]; then
      COMPLETION="$NEXT_WORD"
    fi
  fi

  # Now just set the current line to our partial line + suggested completion
  # and make sure the cursor ends up at the end of the line again
  READLINE_LINE="$STRIPPED_LINE$COMPLETION"
  READLINE_POINT="${#READLINE_LINE}"
}

_history_back() {
  if [[ "$HISTORY_POS" == 0 ]]; then
    HISTORY_CACHE="$READLINE_LINE"
  fi
  HISTORY_POS=$(expr $HISTORY_POS + 1)
  READLINE_LINE=$(tail -n $HISTORY_POS "$HISTORY_FILE" | head -n 1)
  READLINE_POINT="${#READLINE_LINE}"
}

_history_forward() {
  if [[ "$HISTORY_POS" == 0 ]]; then
    return 0
  fi

  HISTORY_POS=$(expr $HISTORY_POS - 1)

  if [[ "$HISTORY_POS" == 0 ]]; then
    READLINE_LINE="$HISTORY_CACHE"
  else
    READLINE_LINE=$(tail -n $HISTORY_POS "$HISTORY_FILE" | head -n 1)
  fi

  READLINE_POINT="${#READLINE_LINE}"
}

# AWS UTILS
_is_path() {
  RES=$(_s3 "s3://$1" 2>&1 > /dev/null)
  RES_STATUS="$?"
  if [[ "$RES_STATUS" != 0 ]]; then
    echo "$(tput setaf 1)$RES$(tput sgr0)"
  fi
  return $RES_STATUS
}

# COMMANDS
_ls() {
  local p=$(_combine_paths "$CURRENT_PATH" "${1:-.}")

  _is_path "$p" || {
    echo "cannot access '$1': no such s3 file or directory" >&2
    return 1
  }

#  local res=$(aws s3 ls "s3://$p")
  _s3 --human-readable "s3://$p" | sed -E 's/^.+ //'
}


_pwd() {
  echo "s3://$CURRENT_PATH"
}

_exit() {
  # TODO: Truncate history file to $MAX_HISTORY_LINES if necessary
  exit "${1:-0}"
}

# MAIN PROMPT

_prompt() {
  local BASE_CMD=''
  local ARGS=''
  local cmd=''

  read -ep "$(eval 'echo -n "'"$PROMPT"'"')" cmd

  echo "$cmd" >> "$HISTORY_FILE"
  HISTORY_POS=0

  if echo "$cmd" | fgrep ' ' &> /dev/null; then
    BASE_CMD=$(echo "$cmd" | cut -d ' ' -f 1)
    ARGS=$(echo "$cmd" | cut -d ' ' -f 2-)
  else
    BASE_CMD="$cmd"
    ARGS=''
  fi

  case "$BASE_CMD" in
    cd)
      _cd $ARGS
      ;;
    ls)
      _ls $ARGS
      ;;
    pwd)
      _pwd $ARGS
      ;;
    clear)
      clear
      ;;
    exit)
      _exit $ARGS
      ;;
    *)
      echo "Unrecognised command: '$BASE_CMD'" >&2
      return 1
      ;;
  esac
}

_cd() {
  local NEW_PATH="$1"
  NEW_PATH="$(_combine_paths "$CURRENT_PATH" "$NEW_PATH/")"

  _is_path "$NEW_PATH" || {
    echo "cannot access '$1': no such s3 directory" >&2
    return 1
  }

  if [[ "$NEW_PATH" == '/' ]]; then
    NEW_PATH=''
  fi

  CURRENT_PATH="$NEW_PATH"
}

if [[ "$#" != 0 ]]; then
  _cd "$1"
fi

bind -x '"\t":"_autocomplete_path"'
bind -x '"\e[A":"_history_back"'
bind -x '"\e[B":"_history_forward"'

while true; do
  _prompt
done
