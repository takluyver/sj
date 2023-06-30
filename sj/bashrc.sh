# Run the regular bashrc file
source ~/.bashrc

if [[ -z "$PROMPT_COMMAND" ]]; then
  export PROMPT_COMMAND="$SJ_UPDATE_COMMAND"
else
  export PROMPT_COMMAND="$PROMPT_COMMAND;$SJ_UPDATE_COMMAND"
fi
