_todo_completion() {
    COMPREPLY=()
    local word=${COMP_WORDS[COMP_CWORD]}
    
    local -a response
    response=($(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD _TODO_COMPLETE=bash_complete todo))
    
    for (( i=0; i<${#response[@]}; i++ )); do
        local type="${response[i]}"
        let i++
        local key="${response[i]}"
        let i++
        local descr="${response[i]}"

        if [[ "$type" == "plain" ]]; then
            if [[ "$descr" == "_" ]]; then
                COMPREPLY+=("$key")
            else
                COMPREPLY+=("$key")
            fi
        elif [[ "$type" == "dir" ]]; then
            COMPREPLY=( $(compgen -d -- $word) )
        elif [[ "$type" == "file" ]]; then
            COMPREPLY=( $(compgen -f -- $word) )
        fi
    done

    return 0
}

complete -F _todo_completion todo

