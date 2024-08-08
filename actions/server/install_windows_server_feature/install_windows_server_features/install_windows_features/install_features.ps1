$FEATURES_INPUT = "{{ FEATURES_TO_INSTALL }}"


function Parse-MultivaluedActionInput($input_string) {
    
    # Trim brackets and Split the python array string on comma char
    $len = $input_string.Length
    if ($len -gt 2) {
        $input_list = $input_string.Substring(1, $len-2).split(",")
    }

    # Trim spaces, and remove single quotes
    $values = @()
    foreach ($i in $input_list) {
        $value = $i.Trim()
        $value = $value.Substring(1, $value.Length-2)
        $values += $value
    }

    Return $values
}

if (
    $FEATURES_INPUT.Substring(0, 1) -ne "[" -or 
    $FEATURES_INPUT.Substring($FEATURES_INPUT.Length-1, 1) -ne "]"
) {
    echo "Invalid input. Make sure ""Allow Multiple Values"" is checked on your Action Input."
    exit 1
}

$FEATURES = Parse-MultivaluedActionInput -input_string $FEATURES_INPUT


foreach ($feature in $FEATURES) {
    Install-WindowsFeature -name $feature -quiet
}

Get-WindowsFeature | Where-Object { $_.Name -in $FEATURES } | Format-Table