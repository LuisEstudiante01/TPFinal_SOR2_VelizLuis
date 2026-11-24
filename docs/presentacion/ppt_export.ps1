param(
    [Parameter(Mandatory = $true)][string]$Pptx,
    [Parameter(Mandatory = $true)][string]$Pdf
)

# Exports a presentation to PDF with Microsoft PowerPoint, so chart numbers use
# the Windows regional format (decimal comma in es-AR) and Office fonts are embedded.
$ErrorActionPreference = 'Stop'
$ppt = New-Object -ComObject PowerPoint.Application
try {
    # Open(FileName, ReadOnly, Untitled, WithWindow)
    $presentation = $ppt.Presentations.Open($Pptx, -1, 0, 0)
    try {
        $presentation.SaveAs($Pdf, 32)  # 32 = ppSaveAsPDF
    } finally {
        $presentation.Close()
    }
} finally {
    $ppt.Quit()
}
