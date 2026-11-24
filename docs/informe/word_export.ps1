param(
    [Parameter(Mandatory = $true)][string]$Docx,
    [Parameter(Mandatory = $true)][string]$Pdf
)

$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
try {
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $document = $word.Documents.Open($Docx, $false, $true)
    try {
        $document.Repaginate()
        foreach ($toc in $document.TablesOfContents) { $toc.Update() }
        $document.Fields.Update() | Out-Null
        foreach ($toc in $document.TablesOfContents) { $toc.Update() }
        $document.Repaginate()
        $document.ExportAsFixedFormat($Pdf, 17, $false, 0, 0, 1, 1, 0, $true, 1, 0, $true, $true, $true)
    } finally {
        $document.Close([ref]0)
    }
} finally {
    $word.Quit([ref]0)
}
