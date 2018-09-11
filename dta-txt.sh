#!/bin/bash
set -e
xsltproc --version &>/dev/null # needed
test -d dta_komplett_*/ && cd $_ || {
    wget http://media.dwds.de/dta/download/dta_komplett_2017-09-01.zip && \
        unzip dta_komplett_2017-09-01.zip
    cd dta_komplett_2017-09-01
    }
mkdir -p txt
test -f tcf-extract-txt.xsl || cat <<EOF > tcf-extract-txt.xsl
<xsl:stylesheet
    version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:tcf="http://www.dspin.de/data/textcorpus">
  <!-- rid of xml syntax: -->  
  <xsl:output
      method="text"
      standalone="yes"
      omit-xml-declaration="yes"/>
  <!-- copy text element verbatim: -->  
  <xsl:template match="tcf:TextCorpus">
    <xsl:value-of select="tcf:text" disable-output-escaping="yes"/>
    <xsl:apply-templates/>
  </xsl:template>
  <!-- override implicit rules copying elements and attributes: -->
  <xsl:template match="text()"/>
</xsl:stylesheet>
EOF
for file in simple/*.xml
do
    outfile=txt/${file#simple/}
    xsltproc tcf-extract-txt.xsl $file > ${outfile%.xml}.txt
done
