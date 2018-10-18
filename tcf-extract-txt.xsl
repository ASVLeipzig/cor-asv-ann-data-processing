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
