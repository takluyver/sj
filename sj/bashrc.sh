# Run the regular bashrc file
source ~/.bashrc

# Set up piping to redsnail
export PROMPT_COMMAND='$SJ_UPDATE_COMMAND "hist1=$(history 1)"'
