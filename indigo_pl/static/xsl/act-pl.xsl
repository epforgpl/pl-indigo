<?xml version="1.0"?>

<!-- ############################################################## -->
<!-- THIS FILE IS USED TO RENDER HTML SEEN IN THE MAIN INDIGO PANEL -->
<!-- ############################################################## -->

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"
  xmlns:a="http://www.akomantoso.org/2.0"
  exclude-result-prefixes="a">

  <xsl:output method="html" />
  <!-- base URL of the resolver for resolving ref elements -->
  <xsl:param name="resolverUrl" />
  <!-- default ID scoping to fall back on if we can't find an appropriate one for a node -->
  <xsl:param name="defaultIdScope" />
  <!-- fully-qualified manifestation URL -->
  <xsl:param name="manifestationUrl" />
  <!-- 3-letter language code of document -->
  <xsl:param name="lang" />



  <!-- ################ -->
  <!-- MAJOR CONTAINERS -->
  <!-- ################ -->

  <xsl:template match="a:act">
    <xsl:element name="article" namespace="">
      <xsl:attribute name="class">akn-act</xsl:attribute>
      <xsl:apply-templates select="@*" />
      <xsl:apply-templates select="a:coverPage" />
      <xsl:apply-templates select="a:preface" />
      <xsl:apply-templates select="a:preamble" />
      <xsl:apply-templates select="a:body" />
      <xsl:apply-templates select="a:conclusions" />
    </xsl:element>
  </xsl:template>

  <xsl:template match="a:part">
    <section class="akn-part">
      <xsl:apply-templates select="@*" />
      <h2>
        <xsl:text>CZĘŚĆ </xsl:text>
        <xsl:variable name="parttype" select="./a:num"/>
        <xsl:choose>
          <xsl:when test="$parttype = 'ogolna'">
            <xsl:text>OGÓLNA</xsl:text>
          </xsl:when>
          <xsl:when test="$parttype = 'szczegolna'">
            <xsl:text>SZCZEGÓLNA</xsl:text>
          </xsl:when>
          <xsl:when test="$parttype = 'wojskowa'">
            <xsl:text>WOJSKOWA</xsl:text>
          </xsl:when>
          <xsl:otherwise>
            <xsl:text>[UNKNOWN TYPE]</xsl:text>
          </xsl:otherwise>
        </xsl:choose>
        <br/>
        <xsl:value-of select="./a:heading" />
      </h2>
      <xsl:apply-templates select="./*[not(self::a:num) and not(self::a:heading)]" />
    </section>
  </xsl:template>

  <xsl:template match="a:book">
    <section class="akn-book">
      <xsl:apply-templates select="@*" />
      <h2>
        <xsl:text>KSIĘGA </xsl:text>
        <xsl:value-of select="./a:num" />
        <br/>
        <xsl:value-of select="./a:heading" />
      </h2>
      <xsl:apply-templates select="./*[not(self::a:num) and not(self::a:heading)]" />
    </section>
  </xsl:template>

  <xsl:template match="a:title">
    <section class="akn-title">
      <xsl:apply-templates select="@*" />
      <h2>
        <xsl:text>TYTUŁ </xsl:text>
        <xsl:value-of select="./a:num" />
        <br/>
        <xsl:value-of select="./a:heading" />
      </h2>
      <xsl:apply-templates select="./*[not(self::a:num) and not(self::a:heading)]" />
    </section>
  </xsl:template>

  <xsl:template match="a:division">
    <section class="akn-division">
      <xsl:apply-templates select="@*" />
      <h2>
        <xsl:text>Dział </xsl:text>
        <xsl:value-of select="./a:num" />
        <br/>
        <xsl:value-of select="./a:heading" />
      </h2>
      <xsl:apply-templates select="./*[not(self::a:num) and not(self::a:heading)]" />
    </section>
  </xsl:template>

  <xsl:template match="a:chapter">
    <section class="akn-chapter">
      <xsl:apply-templates select="@*" />
      <h2>
        <xsl:text>Rozdział </xsl:text>
        <xsl:value-of select="./a:num" />
        <br/>
        <xsl:value-of select="./a:heading" />
      </h2>
      <xsl:apply-templates select="./*[not(self::a:num) and not(self::a:heading)]" />
    </section>
  </xsl:template>

  <xsl:template match="a:subdivision">
    <section class="akn-subdivision">
      <xsl:apply-templates select="@*" />
      <h2>
        <xsl:text>Oddział </xsl:text>
        <xsl:value-of select="./a:num" />
        <br/>
        <xsl:value-of select="./a:heading" />
      </h2>
      <xsl:apply-templates select="./*[not(self::a:num) and not(self::a:heading)]" />
    </section>
  </xsl:template>

  <xsl:template match="a:section[@refersTo='statute']">
    <section class="akn-section">
      <xsl:apply-templates select="@*" />
      <h3>
        <xsl:text>Art. </xsl:text>
        <xsl:call-template name="number-with-superscript"/>
      </h3>
      <xsl:apply-templates select="./*[not(self::a:num)]" />
    </section>
  </xsl:template>

  <xsl:template match="a:section[@refersTo='ordinance']">
    <section class="akn-section">
      <xsl:apply-templates select="@*" />
      <h3>
        <xsl:text>§ </xsl:text>
        <xsl:call-template name="number-with-superscript"/>
      </h3>
      <xsl:apply-templates select="./*[not(self::a:num)]" />
    </section>
  </xsl:template>

  <xsl:template match="a:subsection[@refersTo='noncode_level1_unit']">
    <section class="akn-subsection">
      <xsl:if test="a:num != ''">
        <h4>
          <xsl:value-of select="a:num"/>
          <xsl:text>. </xsl:text>
        </h4>
      </xsl:if>
      <xsl:apply-templates select="./*[not(self::a:num)]" />
    </section>
  </xsl:template>

  <xsl:template match="a:subsection[@refersTo='code_level1_unit']">
    <section class="akn-subsection">
      <h4>
        <xsl:text>§ </xsl:text>
        <xsl:value-of select="a:num" />
        <xsl:text>. </xsl:text>
      </h4>
      <xsl:apply-templates select="./*[not(self::a:num)]" />
    </section>
  </xsl:template>

  <xsl:template match="a:indent[@refersTo='single_tiret']">
    <div class="akn-indent">
      <xsl:apply-templates select="@*" />
      <div class="akn-indent-num">
        <xsl:text>– </xsl:text>
      </div>
      <xsl:apply-templates select="./a:content/a:p"/>
    </div>
  </xsl:template>

  <xsl:template match="a:indent[@refersTo='double_tiret']">
    <div class="akn-indent">
      <xsl:apply-templates select="@*" />
      <div class="akn-indent-num">
        <xsl:text>– – </xsl:text>
      </div>
      <xsl:apply-templates select="./a:content/a:p"/>
    </div>
  </xsl:template>

  <xsl:template match="a:indent[@refersTo='triple_tiret']">
    <div class="akn-indent">
      <xsl:apply-templates select="@*" />
      <div class="akn-indent-num">
        <xsl:text>– – – </xsl:text>
      </div>
      <xsl:apply-templates select="./a:content/a:p"/>
    </div>
  </xsl:template>

  <!-- for general block elements, generate a div -->
  <xsl:template match="a:intro | a:point | a:paragraph | a:subparagraph | a:list | a:wrapUp">
    <div class="akn-{local-name()}">
      <xsl:apply-templates select="@*" />
      <xsl:apply-templates />
    </div>
  </xsl:template>



  <!-- ############ -->
  <!-- OTHER THINGS -->
  <!-- ############ -->

  <xsl:template match="a:docNumber">
    <h3 class="akn-{local-name()} text-center">
      <xsl:apply-templates select="@*" />
      <xsl:apply-templates />
    </h3>
    <br/><br/>
  </xsl:template>

  <xsl:template match="a:docType">
    <h1 class="akn-{local-name()} text-center">
      <xsl:choose>
        <xsl:when test=". = 'statute'"><xsl:text>USTAWA</xsl:text></xsl:when>
        <xsl:when test=". = 'ordinance'"><xsl:text>ROZPORZĄDZENIE</xsl:text></xsl:when>
        <xsl:otherwise><xsl:text>ERROR</xsl:text></xsl:otherwise>
      </xsl:choose>
    </h1>
  </xsl:template>
  
  <xsl:template match="a:docDate">
    <h1 class="akn-{local-name()} text-center">
      <xsl:apply-templates select="@*" />
      <xsl:apply-templates />
    </h1>
  </xsl:template>

  <xsl:template match="a:docTitle">
    <h1 class="akn-{local-name()} text-center">
      <xsl:apply-templates select="@*" />
      <xsl:apply-templates />
    </h1>
  </xsl:template>

  <!-- helper to build an id attribute with an arbitrary value, scoped to the containing doc (if necessary) -->
  <xsl:template name="scoped-id">
    <xsl:param name="id" select="." />

    <xsl:attribute name="id">
      <!-- scope the id to the containing doc, if any, using a default if provided -->
      <xsl:variable name="prefix" select="./ancestor::a:doc[@name][1]/@name"/>
      <xsl:choose>
        <xsl:when test="$prefix != ''">
          <xsl:value-of select="concat($prefix, '/')" />
        </xsl:when>
        <xsl:when test="$defaultIdScope != ''">
          <xsl:value-of select="concat($defaultIdScope, '/')" />
        </xsl:when>
      </xsl:choose>

      <xsl:value-of select="$id" />
    </xsl:attribute>
  </xsl:template>

  <!-- id attribute is scoped if necessary, and the original saved as data-id -->
  <xsl:template match="@id">
    <xsl:call-template name="scoped-id">
      <xsl:with-param name="id" select="." />
    </xsl:call-template>

    <xsl:attribute name="data-id">
      <xsl:value-of select="." />
    </xsl:attribute>
  </xsl:template>

  <!-- copy over attributes using a data- prefix, except for 'id' which is prefixed if necessary as-is -->
  <xsl:template match="@*">
    <xsl:variable name="attName" select="concat('data-', local-name(.))"/>
    <xsl:attribute name="{$attName}">
      <xsl:value-of select="." />
    </xsl:attribute>
  </xsl:template>

  <!-- components/schedules -->
  <xsl:template match="a:doc">
    <!-- a:doc doesn't an id, so add one -->
    <article class="akn-doc" id="{@name}">
      <xsl:apply-templates select="@*" />
      <xsl:if test="a:meta/a:identification/a:FRBRWork/a:FRBRalias">
        <h2>
          <xsl:value-of select="a:meta/a:identification/a:FRBRWork/a:FRBRalias/@value" />
        </h2>
      </xsl:if>

      <xsl:apply-templates select="a:coverPage" />
      <xsl:apply-templates select="a:preface" />
      <xsl:apply-templates select="a:preamble" />
      <xsl:apply-templates select="a:mainBody" />
      <xsl:apply-templates select="a:conclusions" />
    </article>
  </xsl:template>

  <!-- for top-level block elements, generate a span element with a class matching
       the AN name of the node and copy over the attributes -->
  <xsl:template match="a:coverPage | a:preface | a:preamble | a:conclusions">
    <section class="akn-{local-name()}">
      <!-- these components don't have ids in AKN, so add them -->
      <xsl:call-template name="scoped-id">
        <xsl:with-param name="id" select="local-name()" />
      </xsl:call-template>

      <xsl:apply-templates select="@*" />
      <xsl:apply-templates />
      <br/><br/>
    </section>
  </xsl:template>

  <!-- references -->
  <xsl:template match="a:ref">
    <xsl:choose>
      <!-- if it's an absolute URL and there's no resolver URL, don't create an A element -->
      <xsl:when test="starts-with(@href, '/') and $resolverUrl = ''">
        <xsl:call-template name="generic-elem" />
      </xsl:when>

      <xsl:otherwise>
        <!-- Create an A element that links to this ref -->
        <a class="akn-ref" data-href="{@href}">
          <xsl:attribute name="href">
            <xsl:choose>
              <xsl:when test="starts-with(@href, '/')">
                  <xsl:value-of select="concat($resolverUrl, @href)" />
              </xsl:when>
              <xsl:otherwise>
                  <xsl:value-of select="@href" />
              </xsl:otherwise>
            </xsl:choose>
          </xsl:attribute>
          <xsl:copy-of select="@*[local-name() != 'href']" />
          <xsl:apply-templates />
        </a>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- images -->
  <xsl:template match="a:img">
    <img data-src="{@src}">
      <xsl:copy-of select="@*" />

      <!-- make relative image URLs absolute, using the manifestationUrl as a base -->
      <xsl:attribute name="src">
        <xsl:choose>
          <xsl:when test="starts-with(@src, 'http://') or starts-with(@src, 'https://')">
            <!-- already absolute -->
            <xsl:value-of select="@src" />
          </xsl:when>
          <xsl:otherwise>

            <xsl:choose>
              <xsl:when test="starts-with(@src, '/')">
                <xsl:value-of select="concat($manifestationUrl, @src)" />
              </xsl:when>
              <xsl:otherwise>
                <xsl:value-of select="concat($manifestationUrl, '/', @src)" />
              </xsl:otherwise>
            </xsl:choose>

          </xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
    </img>
  </xsl:template>

  <!-- for all nodes, generate a SPAN element with a class matching
       the AN name of the node and copy over the attributes -->
  <xsl:template match="*" name="generic-elem">
    <span class="akn-{local-name()}">
      <xsl:apply-templates select="@*" />
      <xsl:apply-templates />
    </span>
  </xsl:template>
  
  <!-- For HTML table elements, copy them over then apply normal AN
       processing to their contents -->
  <xsl:template match="a:table | a:tr | a:th | a:td">
    <xsl:element name="{local-name()}">
      <xsl:copy-of select="@*" />
      <xsl:apply-templates select="@id" />
      <xsl:apply-templates />
    </xsl:element>
  </xsl:template>

  <!-- special HTML elements -->
  <xsl:template match="a:a">
    <xsl:element name="a">
      <xsl:copy-of select="@href" />
      <xsl:apply-templates select="@*" />
      <xsl:apply-templates />
    </xsl:element>
  </xsl:template>

  <xsl:template match="a:abbr | a:b | a:i | a:span | a:sub | a:sup | a:u">
    <xsl:element name="{local-name()}">
      <xsl:apply-templates select="@*" />
      <xsl:apply-templates />
    </xsl:element>
  </xsl:template>

  <xsl:template match="a:eol">
    <xsl:element name="br" />
  </xsl:template>

  <!-- Helper template to render the number of a given law hierarchy unit, including characters
       in superscript, if needed. Assumes that the number to render is in AKN <num> tag and
       that if there's a superscript to render, it will be after a "^" character. -->
  <xsl:template name="number-with-superscript">
    <!-- No regexes in XSLT 1.0 :( -->
    <xsl:if test="contains(a:num, '^')">
      <xsl:value-of select="substring-before(a:num, '^')"/>
      <sup><xsl:value-of select="substring-after(a:num, '^')"/></sup>
    </xsl:if>
    <xsl:if test="not(contains(a:num, '^'))">
      <xsl:value-of select="a:num"/>
    </xsl:if>
    <xsl:text>.</xsl:text>
  </xsl:template>

</xsl:stylesheet>
