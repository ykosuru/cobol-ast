/*
 * Cobol.g4 Grammar file to parse Cobol files into AST
 * This includes more modern constructs
 */
grammar Cobol;

// Parser Rules
startRule : compilationUnit EOF ;

compilationUnit : (programUnit | copyStatement)* ;

programUnit : identificationDivision environmentDivision? dataDivision? procedureDivision? programUnit* endProgramStatement?
            | classDefinition | interfaceDefinition | functionDefinition ;

endProgramStatement : END PROGRAM programName DOT ;

identificationDivision : (IDENTIFICATION | ID) DIVISION DOT programIdParagraph identificationDivisionBody* ;

programIdParagraph : PROGRAM_ID DOT programName (IS? (COMMON | INITIAL | LIBRARY | DEFINITION | RECURSIVE) PROGRAM?)? DOT? ;

identificationDivisionBody : authorParagraph | installationParagraph | dateWrittenParagraph | dateCompiledParagraph
                           | securityParagraph | remarksParagraph ;

authorParagraph : AUTHOR DOT ;

installationParagraph : INSTALLATION DOT ;

dateWrittenParagraph : DATE_WRITTEN DOT ;

dateCompiledParagraph : DATE_COMPILED DOT ;

securityParagraph : SECURITY DOT ;

remarksParagraph : REMARKS DOT ;

commentEntry : commentLine* ;

//commentLine : (~('\r' | '\n'))+ ('\r' | '\n')+ | COMMENTENTRYLINE ;

//commentLine : (~('\r' | '\n'))+ | COMMENTENTRYLINE ;

//COMMENT_TEXT : ~('*' | '/' | '$' | 'A'..'Z' | 'a'..'z' | '0'..'9' | '-' | '.') ~[\r\n]* ;

// Then modify the comment rule:
commentLine : COMMENTENTRYLINE  ;

environmentDivision : ENVIRONMENT DIVISION DOT environmentDivisionBody* ;

environmentDivisionBody : configurationSection | specialNamesParagraph | inputOutputSection ;

configurationSection : CONFIGURATION SECTION DOT configurationSectionParagraph* ;

configurationSectionParagraph : sourceComputerParagraph | objectComputerParagraph | specialNamesParagraph | repositoryParagraph ;

sourceComputerParagraph : SOURCE_COMPUTER DOT (computerName (WITH? DEBUGGING MODE)? DOT)? ;

objectComputerParagraph : OBJECT_COMPUTER DOT (computerName objectComputerClause* DOT)? ;

objectComputerClause : memorySizeClause | diskSizeClause | collatingSequenceClause | segmentLimitClause | characterSetClause ;

memorySizeClause : MEMORY SIZE? (integerLiteral | cobolWord) (WORDS | CHARACTERS | MODULES)? ;

diskSizeClause : DISK SIZE? IS? (integerLiteral | cobolWord) (WORDS | MODULES)? ;

collatingSequenceClause : PROGRAM? COLLATING? SEQUENCE (IS? alphabetName+) collatingSequenceClauseAlphanumeric? collatingSequenceClauseNational? ;

collatingSequenceClauseAlphanumeric : FOR? ALPHANUMERIC IS? alphabetName ;

collatingSequenceClauseNational : FOR? NATIONAL IS? alphabetName ;

segmentLimitClause : SEGMENT_LIMIT IS? integerLiteral ;

characterSetClause : CHARACTER SET DOT ;

repositoryParagraph : REPOSITORY DOT repositoryEntry* DOT ;

repositoryEntry : FUNCTION functionName (AS literal)? | FUNCTION ALL INTRINSIC | CLASS className (AS literal)? | INTERFACE interfaceName (AS literal)? ;

specialNamesParagraph : SPECIAL_NAMES DOT (specialNameClause+ DOT)? ;

specialNameClause : channelClause | odtClause | alphabetClause | classClause | currencySignClause | decimalPointClause
                  | symbolicCharactersClause | environmentSwitchNameClause | defaultDisplaySignClause
                  | defaultComputationalSignClause | reserveNetworkClause ;

alphabetClause : alphabetClauseFormat1 | alphabetClauseFormat2 ;

alphabetClauseFormat1 : ALPHABET alphabetName (FOR ALPHANUMERIC)? IS? (EBCDIC | ASCII | STANDARD_1 | STANDARD_2 | NATIVE | cobolWord | alphabetLiterals+) ;

alphabetLiterals : literal (alphabetThrough | alphabetAlso+)? ;

alphabetThrough : (THROUGH | THRU) literal ;

alphabetAlso : ALSO literal+ ;

alphabetClauseFormat2 : ALPHABET alphabetName FOR? NATIONAL IS? (NATIVE | CCSVERSION literal) ;

channelClause : CHANNEL integerLiteral IS? mnemonicName ;

classClause : CLASS className (FOR? (ALPHANUMERIC | NATIONAL))? IS? classClauseThrough+ ;

classClauseThrough : classClauseFrom ((THROUGH | THRU) classClauseTo)? ;

classClauseFrom : identifier | literal ;

classClauseTo : identifier | literal ;

currencySignClause : CURRENCY SIGN? IS? literal (WITH? PICTURE SYMBOL literal)? ;

decimalPointClause : DECIMAL_POINT IS? COMMA ;

defaultComputationalSignClause : DEFAULT (COMPUTATIONAL | COMP)? (SIGN IS?)? (LEADING | TRAILING)? (SEPARATE CHARACTER?) ;

defaultDisplaySignClause : DEFAULT_DISPLAY (SIGN IS?)? (LEADING | TRAILING) (SEPARATE CHARACTER?)? ;

environmentSwitchNameClause : environmentName IS? mnemonicName environmentSwitchNameSpecialNamesStatusPhrase?
                           | environmentSwitchNameSpecialNamesStatusPhrase ;

environmentSwitchNameSpecialNamesStatusPhrase : ON STATUS? IS? condition (OFF STATUS? IS? condition)?
                                             | OFF STATUS? IS? condition (ON STATUS? IS? condition)? ;

odtClause : ODT IS? mnemonicName ;

reserveNetworkClause : RESERVE WORDS? LIST? IS? NETWORK CAPABLE? ;

symbolicCharactersClause : SYMBOLIC CHARACTERS? (FOR? (ALPHANUMERIC | NATIONAL))? symbolicCharacters+ (IN alphabetName)? ;

symbolicCharacters : symbolicCharacter+ (IS | ARE)? integerLiteral+ ;

inputOutputSection : INPUT_OUTPUT SECTION DOT inputOutputSectionParagraph* ;

inputOutputSectionParagraph : fileControlParagraph | ioControlParagraph ;

fileControlParagraph : FILE_CONTROL? (DOT? fileControlEntry)* DOT ;

fileControlEntry : selectClause fileControlClause* ;

selectClause : SELECT OPTIONAL? fileName ;

fileControlClause : assignClause | reserveClause | organizationClause | paddingCharacterClause | recordDelimiterClause
                  | accessModeClause | recordKeyClause | alternateRecordKeyClause | fileStatusClause | passwordClause
                  | relativeKeyClause | sharingClause | lockModeClause ;

assignClause : ASSIGN TO? (DISK | DISPLAY | KEYBOARD | PORT | PRINTER | READER | REMOTE | TAPE | VIRTUAL
                          | (DYNAMIC | EXTERNAL)? assignmentName | literal) ;

reserveClause : RESERVE (NO | integerLiteral) ALTERNATE? (AREA | AREAS)? ;

organizationClause : (ORGANIZATION IS?)? (LINE | RECORD BINARY | RECORD | BINARY)? (SEQUENTIAL | RELATIVE | INDEXED) ;

paddingCharacterClause : PADDING CHARACTER? IS? (qualifiedDataName | literal) ;

recordDelimiterClause : RECORD DELIMITER IS? (STANDARD_1 | IMPLICIT | assignmentName) ;

accessModeClause : ACCESS MODE? IS? (SEQUENTIAL | RANDOM | DYNAMIC | EXCLUSIVE) ;

recordKeyClause : RECORD KEY? IS? qualifiedDataName passwordClause? (WITH? DUPLICATES)? ;

alternateRecordKeyClause : ALTERNATE RECORD KEY? IS? qualifiedDataName passwordClause? (WITH? DUPLICATES)? ;

passwordClause : PASSWORD IS? dataName ;

fileStatusClause : FILE? STATUS IS? qualifiedDataName qualifiedDataName? ;

relativeKeyClause : RELATIVE KEY? IS? qualifiedDataName ;

sharingClause : SHARING WITH? (ALL OTHER | NO OTHER | READ ONLY) ;

lockModeClause : LOCK MODE IS? (MANUAL | AUTOMATIC | EXCLUSIVE) ;

ioControlParagraph : I_O_CONTROL DOT (fileName DOT)? (ioControlClause* DOT)? ;

ioControlClause : rerunClause | sameClause | multipleFileClause | commitmentControlClause ;

rerunClause : RERUN (ON (assignmentName | fileName))? EVERY (rerunEveryRecords | rerunEveryOf | rerunEveryClock) ;

rerunEveryRecords : integerLiteral RECORDS ;

rerunEveryOf : END? OF? (REEL | UNIT) OF fileName ;

rerunEveryClock : integerLiteral CLOCK_UNITS? ;

sameClause : SAME (RECORD | SORT | SORT_MERGE)? AREA? FOR? fileName+ ;

multipleFileClause : MULTIPLE FILE TAPE? CONTAINS? multipleFilePosition+ ;

multipleFilePosition : fileName (POSITION integerLiteral)? ;

commitmentControlClause : COMMITMENT CONTROL FOR? fileName ;

dataDivision : DATA DIVISION DOT dataDivisionSection* ;


//dataDivisionSection : fileSection | dataBaseSection | workingStorageSection | linkageSection | communicationSection
//                    | localStorageSection | screenSection | reportSection | programLibrarySection | dataDescriptionEntry
//                    | copyStatement ;

//dataDivisionSection : section | dataDescriptionEntry | copyStatement ;

dataDivisionSection : fileSection | dataBaseSection | workingStorageSection | linkageSection | communicationSection
                    | localStorageSection | screenSection | reportSection | programLibrarySection 
                    | copyStatement 
                    | dataDescriptionEntry  // keep this last, kept running into issues
                    ;


section : fileSection | dataBaseSection | workingStorageSection | linkageSection | communicationSection
        | localStorageSection | screenSection | reportSection | programLibrarySection ;
        
fileSection : FILE SECTION DOT fileDescriptionEntry* ;

fileDescriptionEntry : (FD | SD) fileName (DOT? fileDescriptionEntryClause)* DOT dataDescriptionGroup* ;

fileDescriptionEntryClause : externalClause | globalClause | blockContainsClause | recordContainsClause
                           | labelRecordsClause | valueOfClause | dataRecordsClause | linageClause | codeSetClause
                           | reportClause | recordingModeClause ;

externalClause : IS? EXTERNAL ;

globalClause : IS? GLOBAL ;

blockContainsClause : BLOCK CONTAINS? integerLiteral blockContainsTo? (RECORDS | CHARACTERS)? ;

blockContainsTo : TO integerLiteral ;

recordContainsClause : RECORD (recordContainsClauseFormat1 | recordContainsClauseFormat2 | recordContainsClauseFormat3) ;

recordContainsClauseFormat1 : CONTAINS? integerLiteral CHARACTERS? ;

recordContainsClauseFormat2 : IS? VARYING IN? SIZE? (FROM? integerLiteral recordContainsTo? CHARACTERS?)? (DEPENDING ON? qualifiedDataName)? ;

recordContainsClauseFormat3 : CONTAINS? integerLiteral recordContainsTo CHARACTERS? ;

recordContainsTo : TO integerLiteral ;

labelRecordsClause : LABEL (RECORD IS? | RECORDS ARE?) (OMITTED | STANDARD | dataName+) ;

valueOfClause : VALUE OF valuePair+ ;

valuePair : systemName IS? (qualifiedDataName | literal) ;

dataRecordsClause : DATA (RECORD IS? | RECORDS ARE?) dataName+ ;

linageClause : LINAGE IS? (dataName | integerLiteral) LINES? linageAt* ;

linageAt : linageFootingAt | linageLinesAtTop | linageLinesAtBottom ;

linageFootingAt : WITH? FOOTING AT? (dataName | integerLiteral) ;

linageLinesAtTop : LINES? AT? TOP (dataName | integerLiteral) ;

linageLinesAtBottom : LINES? AT? BOTTOM (dataName | integerLiteral) ;

recordingModeClause : RECORDING MODE? IS? modeStatement ;

modeStatement : cobolWord ;

codeSetClause : CODE_SET IS? alphabetName ;

reportClause : (REPORT IS? | REPORTS ARE?) reportName+ ;

dataBaseSection : DATA_BASE SECTION DOT dataBaseSectionEntry* ;

dataBaseSectionEntry : integerLiteral literal INVOKE literal ;

// Enhanced Working Storage Section with hierarchical structure
workingStorageSection : WORKING_STORAGE SECTION DOT dataDescriptionGroup* ;

linkageSection : LINKAGE SECTION DOT dataDescriptionGroup* ;

// Enhanced data description group to handle hierarchical relationships
dataDescriptionGroup : dataDescriptionEntryFormat1 subordinateDataItem*
                     | dataDescriptionEntryFormat2
                     | dataDescriptionEntryFormat3
                     | dataDescriptionEntryFormat4
                     | dataDescriptionEntryExecSql  // Add this!
                     | copyStatement ;

subordinateDataItem : dataDescriptionEntryFormat1 subordinateDataItem*
                    | dataDescriptionEntryFormat3  // 88 level conditions
                    | copyStatement ;

communicationSection : COMMUNICATION SECTION DOT (communicationDescriptionEntry | dataDescriptionGroup)* ;

communicationDescriptionEntry : communicationDescriptionEntryFormat1 | communicationDescriptionEntryFormat2
                             | communicationDescriptionEntryFormat3 ;

communicationDescriptionEntryFormat1 : CD cdName FOR? INITIAL? INPUT 
                                     (communicationClause | dataDescName)* DOT 
                                     dataDescriptionGroup* ;

communicationDescriptionEntryFormat2 : CD cdName FOR? OUTPUT 
                                     (outputCommunicationClause | dataDescName)* DOT 
                                     dataDescriptionGroup* ;

communicationDescriptionEntryFormat3 : CD cdName FOR? INITIAL I_O 
                                     (ioCommunicationClause | dataDescName)* DOT 
                                     dataDescriptionGroup* ;

// Enhanced communication clauses
communicationClause : symbolicQueueClause | symbolicSubQueueClause | messageDateClause | messageTimeClause 
                    | symbolicSourceClause | textLengthClause | endKeyClause | statusKeyClause | messageCountClause ;

outputCommunicationClause : destinationCountClause | textLengthClause | statusKeyClause | destinationTableClause 
                          | errorKeyClause | symbolicDestinationClause ;

ioCommunicationClause : messageDateClause | messageTimeClause | symbolicTerminalClause | textLengthClause 
                      | endKeyClause | statusKeyClause ;

destinationCountClause : DESTINATION COUNT IS? dataDescName ;

destinationTableClause : DESTINATION TABLE OCCURS integerLiteral TIMES (INDEXED BY indexName+)? ;

endKeyClause : END KEY IS? dataDescName ;

errorKeyClause : ERROR KEY IS? dataDescName ;

messageCountClause : MESSAGE? COUNT IS? dataDescName ;

messageDateClause : MESSAGE DATE IS? dataDescName ;

messageTimeClause : MESSAGE TIME IS? dataDescName ;

statusKeyClause : STATUS KEY IS? dataDescName ;

symbolicDestinationClause : SYMBOLIC? DESTINATION IS? dataDescName ;

symbolicQueueClause : SYMBOLIC? QUEUE IS? dataDescName ;

symbolicSourceClause : SYMBOLIC? SOURCE IS? dataDescName ;

symbolicTerminalClause : SYMBOLIC? TERMINAL IS? dataDescName ;

symbolicSubQueueClause : SYMBOLIC? (SUB_QUEUE_1 | SUB_QUEUE_2 | SUB_QUEUE_3) IS? dataDescName ;

textLengthClause : TEXT LENGTH IS? dataDescName ;

localStorageSection : LOCAL_STORAGE SECTION DOT (LD localName DOT)? dataDescriptionGroup* ;

screenSection : SCREEN SECTION DOT screenDescriptionEntry* ;

screenDescriptionEntry : integerLevelNumber (FILLER | screenName)? screenDescriptionClause* DOT ;

screenDescriptionClause : screenDescriptionBlankClause | screenDescriptionBellClause | screenDescriptionBlinkClause
                        | screenDescriptionEraseClause | screenDescriptionLightClause | screenDescriptionGridClause
                        | screenDescriptionReverseVideoClause | screenDescriptionUnderlineClause | screenDescriptionSizeClause
                        | screenDescriptionLineClause | screenDescriptionColumnClause | screenDescriptionForegroundColorClause
                        | screenDescriptionBackgroundColorClause | screenDescriptionControlClause | screenDescriptionValueClause
                        | screenDescriptionPictureClause | (screenDescriptionFromClause | screenDescriptionUsingClause)
                        | screenDescriptionUsageClause | screenDescriptionBlankWhenZeroClause | screenDescriptionJustifiedClause
                        | screenDescriptionSignClause | screenDescriptionAutoClause | screenDescriptionSecureClause
                        | screenDescriptionRequiredClause | screenDescriptionPromptClause | screenDescriptionFullClause
                        | screenDescriptionZeroFillClause ;

screenDescriptionBlankClause : BLANK (SCREEN | LINE) ;

screenDescriptionBellClause : BELL | BEEP ;

screenDescriptionBlinkClause : BLINK ;

screenDescriptionEraseClause : ERASE (EOL | EOS) ;

screenDescriptionLightClause : HIGHLIGHT | LOWLIGHT ;

screenDescriptionGridClause : GRID | LEFTLINE | OVERLINE ;

screenDescriptionReverseVideoClause : REVERSE_VIDEO ;

screenDescriptionUnderlineClause : UNDERLINE ;

screenDescriptionSizeClause : SIZE IS? (identifier | integerLiteral) ;

screenDescriptionLineClause : LINE (NUMBER? IS? (PLUS | PLUSCHAR | MINUSCHAR))? (identifier | integerLiteral) ;

screenDescriptionColumnClause : (COLUMN | COL) (NUMBER? IS? (PLUS | PLUSCHAR | MINUSCHAR))? (identifier | integerLiteral) ;

screenDescriptionForegroundColorClause : (FOREGROUND_COLOR | FOREGROUND_COLOUR) IS? (identifier | integerLiteral) ;

screenDescriptionBackgroundColorClause : (BACKGROUND_COLOR | BACKGROUND_COLOUR) IS? (identifier | integerLiteral) ;

screenDescriptionControlClause : CONTROL IS? identifier ;

screenDescriptionValueClause : (VALUE IS?) literal ;

screenDescriptionPictureClause : (PICTURE | PIC) IS? pictureString ;

screenDescriptionFromClause : FROM (identifier | literal) screenDescriptionToClause? ;

screenDescriptionToClause : TO identifier ;

screenDescriptionUsingClause : USING identifier ;

screenDescriptionUsageClause : (USAGE IS?) (DISPLAY | DISPLAY_1) ;

screenDescriptionBlankWhenZeroClause : BLANK WHEN? ZERO ;

screenDescriptionJustifiedClause : (JUSTIFIED | JUST) RIGHT? ;

screenDescriptionSignClause : (SIGN IS?)? (LEADING | TRAILING) (SEPARATE CHARACTER?)? ;

screenDescriptionAutoClause : AUTO | AUTO_SKIP ;

screenDescriptionSecureClause : SECURE | NO_ECHO ;

screenDescriptionRequiredClause : REQUIRED | EMPTY_CHECK ;

screenDescriptionPromptClause : PROMPT CHARACTER? IS? (identifier | literal) screenDescriptionPromptOccursClause? ;

screenDescriptionPromptOccursClause : OCCURS integerLiteral TIMES? ;

screenDescriptionFullClause : FULL | LENGTH_CHECK ;

screenDescriptionZeroFillClause : ZERO_FILL ;

reportSection : REPORT SECTION DOT reportDescription* ;

reportDescription : reportDescriptionEntry reportGroupDescriptionEntry+ ;

reportDescriptionEntry : RD reportName reportDescriptionGlobalClause? (reportDescriptionPageLimitClause
                        reportDescriptionHeadingClause? reportDescriptionFirstDetailClause? reportDescriptionLastDetailClause?
                        reportDescriptionFootingClause?)? DOT ;

reportDescriptionGlobalClause : IS? GLOBAL ;

reportDescriptionPageLimitClause : PAGE (LIMIT IS? | LIMITS ARE?)? integerLiteral (LINE | LINES)? ;

reportDescriptionHeadingClause : HEADING integerLiteral ;

reportDescriptionFirstDetailClause : FIRST DETAIL integerLiteral ;

reportDescriptionLastDetailClause : LAST DETAIL integerLiteral ;

reportDescriptionFootingClause : FOOTING integerLiteral ;

reportGroupDescriptionEntry : reportGroupDescriptionEntryFormat1 | reportGroupDescriptionEntryFormat2
                            | reportGroupDescriptionEntryFormat3 ;

reportGroupDescriptionEntryFormat1 : integerLevelNumber dataName reportGroupLineNumberClause? reportGroupNextGroupClause?
                                   reportGroupTypeClause reportGroupUsageClause? DOT ;

reportGroupDescriptionEntryFormat2 : integerLevelNumber dataName? reportGroupLineNumberClause? reportGroupUsageClause DOT ;

reportGroupDescriptionEntryFormat3 : integerLevelNumber dataName? reportGroupClause* DOT ;

reportGroupClause : reportGroupPictureClause | reportGroupUsageClause | reportGroupSignClause | reportGroupJustifiedClause
                  | reportGroupBlankWhenZeroClause | reportGroupLineNumberClause | reportGroupColumnNumberClause
                  | (reportGroupSourceClause | reportGroupValueClause | reportGroupSumClause | reportGroupResetClause)
                  | reportGroupIndicateClause ;

reportGroupPictureClause : (PICTURE | PIC) IS? pictureString ;

reportGroupUsageClause : (USAGE IS?)? (DISPLAY | DISPLAY_1) ;

reportGroupSignClause : SIGN IS? (LEADING | TRAILING) SEPARATE CHARACTER? ;

reportGroupJustifiedClause : (JUSTIFIED | JUST) RIGHT? ;

reportGroupBlankWhenZeroClause : BLANK WHEN? ZERO ;

reportGroupLineNumberClause : LINE? NUMBER? IS? (reportGroupLineNumberNextPage | reportGroupLineNumberPlus) ;

reportGroupLineNumberNextPage : integerLiteral (ON? NEXT PAGE)? ;

reportGroupLineNumberPlus : PLUS integerLiteral ;

reportGroupColumnNumberClause : COLUMN NUMBER? IS? integerLiteral ;

reportGroupSourceClause : SOURCE IS? identifier ;

reportGroupValueClause : VALUE IS? literal ;

reportGroupSumClause : SUM identifier (COMMA_CHAR? identifier)* (UPON dataName (COMMA_CHAR? dataName)*)? ;

reportGroupResetClause : RESET ON? (FINAL | dataName) ;

reportGroupIndicateClause : GROUP INDICATE? ;

reportGroupNextGroupClause : NEXT GROUP IS? (integerLiteral | reportGroupNextGroupNextPage | reportGroupNextGroupPlus) ;

reportGroupNextGroupNextPage : NEXT PAGE ;

reportGroupNextGroupPlus : PLUS integerLiteral ;

reportGroupTypeClause : TYPE IS? (reportGroupTypeReportHeading | reportGroupTypePageHeading | reportGroupTypeControlHeading
                        | reportGroupTypeDetail | reportGroupTypeControlFooting | reportGroupTypePageFooting
                        | reportGroupTypeReportFooting) ;

reportGroupTypeReportHeading : REPORT HEADING | RH ;

reportGroupTypePageHeading : PAGE HEADING | PH ;

reportGroupTypeControlHeading : (CONTROL HEADING | CH) (FINAL | dataName) ;

reportGroupTypeDetail : DETAIL | DE ;

reportGroupTypeControlFooting : (CONTROL FOOTING | CF) (FINAL | dataName) ;

reportGroupTypePageFooting : PAGE FOOTING | PF ;

reportGroupTypeReportFooting : REPORT FOOTING | RF ;

programLibrarySection : PROGRAM_LIBRARY SECTION DOT libraryDescriptionEntry* ;

libraryDescriptionEntry : libraryDescriptionEntryFormat1 | libraryDescriptionEntryFormat2 ;

libraryDescriptionEntryFormat1 : LD libraryName EXPORT libraryAttributeClauseFormat1? libraryEntryProcedureClauseFormat1? ;

libraryDescriptionEntryFormat2 : LB libraryName IMPORT libraryIsGlobalClause? libraryIsCommonClause?
                               (libraryAttributeClauseFormat2 | libraryEntryProcedureClauseFormat2)* ;

libraryAttributeClauseFormat1 : ATTRIBUTE (SHARING IS? (DONTCARE | PRIVATE | SHAREDBYRUNUNIT | SHAREDBYALL))? ;

libraryAttributeClauseFormat2 : ATTRIBUTE libraryAttributeFunction? (LIBACCESS IS? (BYFUNCTION | BYTITLE))?
                               libraryAttributeParameter? libraryAttributeTitle? ;

libraryAttributeFunction : FUNCTIONNAME IS literal ;

libraryAttributeParameter : LIBPARAMETER IS? literal ;

libraryAttributeTitle : TITLE IS? literal ;

libraryEntryProcedureClauseFormat1 : ENTRY_PROCEDURE programName libraryEntryProcedureForClause? ;

libraryEntryProcedureClauseFormat2 : ENTRY_PROCEDURE programName libraryEntryProcedureForClause?
                                   libraryEntryProcedureWithClause? libraryEntryProcedureUsingClause?
                                   libraryEntryProcedureGivingClause? ;

libraryEntryProcedureForClause : FOR literal ;

libraryEntryProcedureGivingClause : GIVING dataName ;

libraryEntryProcedureUsingClause : USING libraryEntryProcedureUsingName+ ;

libraryEntryProcedureUsingName : dataName | fileName ;

libraryEntryProcedureWithClause : WITH libraryEntryProcedureWithName+ ;

libraryEntryProcedureWithName : localName | fileName ;

libraryIsCommonClause : IS? COMMON ;

libraryIsGlobalClause : IS? GLOBAL ;

copyStatement : COPY copyName (OF | IN)? libraryName? (REPLACING copyReplacingPhrase)? DOT ;

copyName : literal | cobolWord ;

copyReplacingPhrase : copyReplacingOperand+ ;

copyReplacingOperand : (LEADING | TRAILING)? copyReplacingItem BY copyReplacingItem ;

copyReplacingItem : literal | cobolWord | pseudoText ;

pseudoText : PSEUDO_TEXT_DELIMITER pseudoTextContent* PSEUDO_TEXT_DELIMITER ;

pseudoTextContent : ~(PSEUDO_TEXT_DELIMITER)+ ;

// Enhanced data description entries with proper level number support
dataDescriptionEntryFormat4 : LEVEL_NUMBER_77 dataName dataClause* DOT ;

dataDescriptionEntryFormat1 : integerLevelNumber (FILLER | dataName)? dataClause* DOT ;

dataDescriptionEntryFormat2 : LEVEL_NUMBER_66 dataName dataRenamesClause DOT ;

dataDescriptionEntryFormat3 : LEVEL_NUMBER_88 conditionName dataValueClause DOT ;

dataDescriptionEntryExecSql : EXEC sqlStatement END_EXEC DOT? ;

dataDescriptionEntry : dataDescriptionEntryFormat1 | dataDescriptionEntryFormat2 | dataDescriptionEntryFormat3
                     | dataDescriptionEntryFormat4 | dataDescriptionEntryExecSql | copyStatement ;

// keep dataValueClause at the front of the list
dataClause : dataValueClause | dataRedefinesClause | dataIntegerStringClause | dataExternalClause | dataGlobalClause | dataTypeDefClause
           | dataThreadLocalClause | dataPictureClause | dataCommonOwnLocalClause | dataTypeClause | dataUsingClause
           | dataUsageClause | dataReceivedByClause | dataOccursClause | dataSignClause
           | dataSynchronizedClause | dataJustifiedClause | dataBlankWhenZeroClause | dataWithLowerBoundsClause
           | dataAlignedClause | dataRecordAreaClause | dataVolatileClause | dataBasedClause ;


dataRedefinesClause : REDEFINES dataName ;

dataIntegerStringClause : INTEGER | STRING ;

dataExternalClause : IS? EXTERNAL (BY literal)? ;

dataGlobalClause : IS? GLOBAL ;

dataTypeDefClause : IS? TYPEDEF ;

dataThreadLocalClause : IS? THREAD_LOCAL ;

dataPictureClause : (PICTURE | PIC) IS? pictureString ;

pictureString : (pictureChars+ pictureCardinality?)+ ;

pictureChars : DOLLAR | AMPERSAND | LBRACKET | RBRACKET | IDENTIFIER | INTEGERLITERAL | NUMERICLITERAL | SLASH
             | COMMA_CHAR | DOT | COLON | ASTERISK | DOUBLEASTERISK | PLUSCHAR | MINUSCHAR | LESSTHANCHAR
             | MORETHANCHAR | 'X' | 'A' | 'N' | 'S' | 'V' | 'P' | 'Z' | 'B' | 'E' | 'G' | 'U' ;

pictureCardinality : LPARENCHAR (INTEGERLITERAL | NUMERICLITERAL) RPARENCHAR ;

dataCommonOwnLocalClause : COMMON | OWN | LOCAL ;

dataTypeClause : TYPE IS? (SHORT_DATE | LONG_DATE | NUMERIC_DATE | NUMERIC_TIME | LONG_TIME | TIMESTAMP
                         | TIMESTAMP_WITH_TIMEZONE | (CLOB | BLOB | DBCLOB) LPARENCHAR integerLiteral RPARENCHAR) ;

dataUsingClause : USING (LANGUAGE | CONVENTION) OF? (cobolWord | dataName) ;

dataUsageClause : (USAGE IS?)? (BINARY (TRUNCATED | EXTENDED)? | BIT | COMP | COMP_1 | COMP_2 | COMP_3 | COMP_4
                | COMP_5 | COMP_6 | COMPUTATIONAL | COMPUTATIONAL_1 | COMPUTATIONAL_2 | COMPUTATIONAL_3
                | COMPUTATIONAL_4 | COMPUTATIONAL_5 | COMPUTATIONAL_6 | CONTROL_POINT | DATE | DISPLAY
                | DISPLAY_1 | DOUBLE | EVENT | FLOAT_BINARY_32 | FLOAT_BINARY_64 | FLOAT_DECIMAL_16
                | FLOAT_DECIMAL_34 | FLOAT_EXTENDED | FUNCTION_POINTER | INDEX | KANJI | LOCK | NATIONAL
                | PACKED_DECIMAL | POINTER | PROCEDURE_POINTER | REAL | SQL | TASK | OBJECT_REFERENCE className?
                | UTF_8 | UTF_16) ;

dataValueClause : ((VALUE | VALUES) (IS | ARE)?)? dataValueInterval (COMMA_CHAR? dataValueInterval)* ;

dataValueInterval : dataValueIntervalFrom dataValueIntervalTo? ;

dataValueIntervalFrom : literal | cobolWord ;

dataValueIntervalTo : (THROUGH | THRU) literal ;

dataReceivedByClause : RECEIVED? BY? (CONTENT | REFERENCE | REF) ;

dataOccursClause : OCCURS (identifier | integerLiteral) dataOccursTo? TIMES? dataOccursDepending? (dataOccursSort | dataOccursIndexed)* ;

dataOccursTo : TO integerLiteral ;

dataOccursDepending : DEPENDING ON? qualifiedDataName ;

dataOccursSort : (ASCENDING | DESCENDING) KEY? IS? qualifiedDataName+ ;

dataOccursIndexed : INDEXED BY? LOCAL? indexName+ ;

dataSignClause : (SIGN IS?)? (LEADING | TRAILING) (SEPARATE CHARACTER?)? ;

dataSynchronizedClause : (SYNCHRONIZED | SYNC) (LEFT | RIGHT)? ;

dataJustifiedClause : (JUSTIFIED | JUST) RIGHT? ;

dataBlankWhenZeroClause : BLANK WHEN? (ZERO | ZEROS | ZEROES) ;

dataWithLowerBoundsClause : WITH? LOWER BOUNDS ;

dataAlignedClause : ALIGNED ;

dataRecordAreaClause : RECORD AREA ;

dataVolatileClause : VOLATILE ;

dataBasedClause : BASED ON? qualifiedDataName ;

dataRenamesClause : RENAMES qualifiedDataName ((THROUGH | THRU) qualifiedDataName)? ;

procedureDivision : PROCEDURE DIVISION procedureDivisionUsingClause? procedureDivisionGivingClause? DOT
                  procedureDeclaratives? procedureDivisionBody ;

procedureDeclaratives : DECLARATIVES DOT procedureDeclarative+ END DECLARATIVES DOT ;

procedureDeclarative : procedureSectionHeader DOT useStatement DOT paragraphs ;

procedureSectionHeader : sectionName SECTION integerLiteral? ;

procedureSection : procedureSectionHeader DOT paragraphs ;

procedureDivisionBody : paragraphs procedureSection* ;

procedureDivisionUsingClause : (USING | CHAINING) procedureDivisionUsingParameter+ ;

procedureDivisionUsingParameter : procedureDivisionByReferencePhrase | procedureDivisionByValuePhrase ;

procedureDivisionByReferencePhrase : (BY? REFERENCE)? procedureDivisionByReference+ ;

procedureDivisionByReference : (OPTIONAL? (identifier | fileName)) | ANY ;

procedureDivisionByValuePhrase : BY? VALUE procedureDivisionByValue+ ;

procedureDivisionByValue : identifier | literal | ANY ;

procedureDivisionGivingClause : GIVING (identifier | qualifiedDataName) ;

paragraphs : sentence* paragraph* ;

paragraph : paragraphName DOT? (alteredGoTo | sentence*) ;

sentence : statement* DOT ;

statement : acceptStatement | addStatement | alterStatement | allocateStatement | callStatement | cancelStatement
          | closeStatement | computeStatement | continueStatement | deleteStatement | disableStatement
          | displayStatement | divideStatement | enableStatement | entryStatement | evaluateStatement
          | exhibitStatement | execCicsStatement | execSqlStatement | execSqlImsStatement | exitStatement
          | freeStatement | generateStatement | gobackStatement | goToStatement | ifStatement
          | initializeStatement | initiateStatement | inspectStatement | invokeStatement | jsonGenerateStatement
          | jsonParseStatement | mergeStatement | moveStatement | multiplyStatement | nextSentenceStatement
          | openStatement | performStatement | purgeStatement | raiseStatement | readStatement | receiveStatement
          | releaseStatement | resumeStatement | returnStatement | rewriteStatement | searchStatement
          | sendStatement | setStatement | sortStatement | startStatement | stopStatement | stringStatement
          | subtractStatement | terminateStatement | unstringStatement | writeStatement | xmlGenerateStatement
          | xmlParseStatement ;

acceptStatement : ACCEPT identifier (acceptFromDateStatement | acceptFromEscapeKeyStatement | acceptFromMnemonicStatement
                | acceptMessageCountStatement)? onExceptionClause? notOnExceptionClause? END_ACCEPT? ;

acceptFromDateStatement : FROM (DATE YYYYMMDD? | DAY YYYYDDD? | DAY_OF_WEEK | TIME | TIMER | TODAYS_DATE MMDDYYYY?
                        | TODAYS_NAME | YEAR | YYYYMMDD | YYYYDDD) ;

acceptFromEscapeKeyStatement : FROM ESCAPE KEY ;

acceptFromMnemonicStatement : FROM mnemonicName ;

acceptMessageCountStatement : MESSAGE? COUNT ;

addStatement : ADD (addToStatement | addToGivingStatement | addCorrespondingStatement) onSizeErrorPhrase?
             notOnSizeErrorPhrase? END_ADD? ;

addToStatement : addFrom+ TO addTo+ ;

addToGivingStatement : addFrom+ (TO addToGiving+)? GIVING addGiving+ ;

addCorrespondingStatement : (CORRESPONDING | CORR) identifier TO addTo ;

addFrom : identifier | literal ;

addTo : identifier ROUNDED? ;

addToGiving : identifier | literal ;

addGiving : identifier ROUNDED? ;

allocateStatement : ALLOCATE (integerLiteral | identifier) (CHARACTERS | BYTES)? RETURNING (identifier | ADDRESS OF identifier)
                  onExceptionClause? notOnExceptionClause? END_ALLOCATE? ;

alterStatement : ALTER alterProceedTo+ ;

alterProceedTo : procedureName TO (PROCEED TO)? procedureName ;

alteredGoTo : GO TO? DOT ;

callStatement : CALL (identifier | literal) callUsingPhrase? callGivingPhrase? onOverflowPhrase? onExceptionClause?
              notOnExceptionClause? END_CALL? ;

callUsingPhrase : USING callUsingParameter+ ;

callUsingParameter : callByReferencePhrase | callByValuePhrase | callByContentPhrase ;

callByReferencePhrase : (BY? REFERENCE)? callByReference+ ;

callByReference : ((ADDRESS OF | INTEGER | STRING)? identifier | literal | fileName) | OMITTED ;

callByValuePhrase : BY? VALUE callByValue+ ;

callByValue : (ADDRESS OF | LENGTH OF?)? (identifier | literal) ;

callByContentPhrase : BY? CONTENT callByContent+ ;

callByContent : (ADDRESS OF | LENGTH OF?)? identifier | literal | OMITTED ;

callGivingPhrase : (GIVING | RETURNING) identifier ;

cancelStatement : CANCEL cancelCall+ ;

cancelCall : libraryName (BYTITLE | BYFUNCTION) | identifier | literal ;

closeStatement : CLOSE closeFile+ ;

closeFile : fileName (closeReelUnitStatement | closeRelativeStatement | closePortFileIOStatement)? ;

closeReelUnitStatement : (REEL | UNIT) (FOR? REMOVAL)? (WITH? (NO REWIND | LOCK))? ;

closeRelativeStatement : WITH? (NO REWIND | LOCK) ;

closePortFileIOStatement : (WITH? NO WAIT | WITH WAIT) (USING closePortFileIOUsing+)? ;

closePortFileIOUsing : closePortFileIOUsingCloseDisposition | closePortFileIOUsingAssociatedData
                      | closePortFileIOUsingAssociatedDataLength ;

closePortFileIOUsingCloseDisposition : CLOSE_DISPOSITION OF? (ABORT | ORDERLY) ;

closePortFileIOUsingAssociatedData : ASSOCIATED_DATA (identifier | integerLiteral) ;

closePortFileIOUsingAssociatedDataLength : ASSOCIATED_DATA_LENGTH OF? (identifier | integerLiteral) ;

computeStatement : COMPUTE computeStore+ EQUALS arithmeticExpression onSizeErrorPhrase? notOnSizeErrorPhrase? END_COMPUTE? ;

computeStore : identifier ROUNDED? ;

continueStatement : CONTINUE ;

deleteStatement : DELETE fileName RECORD? invalidKeyPhrase? notInvalidKeyPhrase? END_DELETE? ;

disableStatement : DISABLE (INPUT TERMINAL? | I_O TERMINAL | OUTPUT) cdName WITH? KEY (identifier | literal) ;

displayStatement : DISPLAY displayOperand+ displayAt? displayUpon? displayWith? onExceptionClause? notOnExceptionClause? END_DISPLAY? ;

displayOperand : identifier | literal ;

displayAt : AT (identifier | literal) ;

displayUpon : UPON (mnemonicName | environmentName) ;

displayWith : WITH? NO ADVANCING ;

divideStatement : DIVIDE (identifier | literal) (divideIntoStatement | divideIntoGivingStatement | divideByGivingStatement)
                divideRemainder? onSizeErrorPhrase? notOnSizeErrorPhrase? END_DIVIDE? ;

divideIntoStatement : INTO divideInto+ ;

divideIntoGivingStatement : INTO (identifier | literal) divideGivingPhrase? ;

divideByGivingStatement : BY (identifier | literal) divideGivingPhrase? ;

divideGivingPhrase : GIVING divideGiving+ ;

divideInto : identifier ROUNDED? ;

divideGiving : identifier ROUNDED? ;

divideRemainder : REMAINDER identifier ;

enableStatement : ENABLE (INPUT TERMINAL? | I_O TERMINAL | OUTPUT) cdName WITH? KEY (literal | identifier) ;

entryStatement : ENTRY literal (USING identifier+)? ;

evaluateStatement : EVALUATE evaluateSelect evaluateAlsoSelect* evaluateWhenPhrase* evaluateWhenOther? END_EVALUATE? ;

evaluateSelect : identifier | literal | arithmeticExpression | condition ;

evaluateAlsoSelect : ALSO evaluateSelect ;

evaluateWhenPhrase : evaluateWhen+ statement* ;

evaluateWhen : WHEN evaluateCondition evaluateAlsoCondition* ;

evaluateCondition : ANY | NOT? evaluateValue evaluateThrough? | condition | booleanLiteral ;

evaluateThrough : (THROUGH | THRU) evaluateValue ;

evaluateAlsoCondition : ALSO evaluateCondition ;

evaluateWhenOther : WHEN OTHER statement* ;

evaluateValue : identifier | literal | arithmeticExpression ;

execCicsStatement : EXEC CICS execCicsLine+ END_EXEC ;

execCicsLine : (IDENTIFIER | literal | operator | DOT | COMMA_CHAR | LPARENCHAR | RPARENCHAR | EQUALS | COLON)+ ;

execSqlStatement : EXEC SQL sqlStatement END_EXEC ;

sqlStatement : (~END_EXEC)* ;

execSqlImsStatement : EXEC SQL IMS execSqlImsLine+ END_EXEC ;

execSqlImsLine : (IDENTIFIER | literal | operator | DOT | COMMA_CHAR | LPARENCHAR | RPARENCHAR | EQUALS | COLON)+ ;

exhibitStatement : EXHIBIT NAMED? CHANGED? exhibitOperand+ ;

exhibitOperand : identifier | literal ;

exitStatement : EXIT (PROGRAM | METHOD | FUNCTION | PERFORM | PARAGRAPH | SECTION)? ;

freeStatement : FREE (identifier | ADDRESS OF identifier) onExceptionClause? notOnExceptionClause? END_FREE? ;

generateStatement : GENERATE reportName ;

gobackStatement : GOBACK (GIVING | RAISING)? (identifier | literal)? ;

goToStatement : GO TO? (goToStatementSimple | goToDependingOnStatement) ;

goToStatementSimple : procedureName ;

goToDependingOnStatement : procedureName+ (DEPENDING ON? identifier)? ;

ifStatement : IF condition ifThen ifElse? END_IF? ;

ifThen : THEN? (NEXT SENTENCE | statement*) ;

ifElse : ELSE (NEXT SENTENCE | statement*) ;

initializeStatement : INITIALIZE identifier+ initializeReplacingPhrase? ;

initializeReplacingPhrase : REPLACING initializeReplacingBy+ ;

initializeReplacingBy : (ALPHABETIC | ALPHANUMERIC | ALPHANUMERIC_EDITED | NATIONAL | NATIONAL_EDITED | NUMERIC
                        | NUMERIC_EDITED | DBCS | EGCS) DATA? BY (identifier | literal) ;

initiateStatement : INITIATE reportName+ ;

inspectStatement : INSPECT identifier (inspectTallyingPhrase | inspectReplacingPhrase | inspectTallyingReplacingPhrase
                 | inspectConvertingPhrase) ;

inspectTallyingPhrase : TALLYING inspectFor+ ;

inspectReplacingPhrase : REPLACING (inspectReplacingCharacters | inspectReplacingAllLeadings)+ ;

inspectTallyingReplacingPhrase : TALLYING inspectFor+ inspectReplacingPhrase+ ;

inspectConvertingPhrase : CONVERTING (identifier | literal) inspectTo inspectBeforeAfter* ;

inspectFor : identifier FOR (inspectCharacters | inspectAllLeadings)+ ;

inspectCharacters : (CHARACTER | CHARACTERS) inspectBeforeAfter* ;

inspectReplacingCharacters : (CHARACTER | CHARACTERS) inspectBy inspectBeforeAfter* ;

inspectAllLeadings : (ALL | LEADING) inspectAllLeading+ ;

inspectReplacingAllLeadings : (ALL | LEADING | FIRST) inspectReplacingAllLeading+ ;

inspectAllLeading : (identifier | literal) inspectBeforeAfter* ;

inspectReplacingAllLeading : (identifier | literal) inspectBy inspectBeforeAfter* ;

inspectBy : BY (identifier | literal) ;

inspectTo : TO (identifier | literal) ;

inspectBeforeAfter : (BEFORE | AFTER) INITIAL? (identifier | literal) ;

invokeStatement : INVOKE (identifier | SELF | SUPER) literal (USING invokeUsingParameter*)? (RETURNING identifier)?
                onExceptionClause? notOnExceptionClause? END_INVOKE? ;

invokeUsingParameter : (BY REFERENCE | BY CONTENT | BY VALUE)? (identifier | literal) ;

jsonGenerateStatement : JSON GENERATE identifier FROM identifier (NAME OF? identifier)? (SUPPRESS identifier*)?
                      onExceptionClause? notOnExceptionClause? END_JSON ;

jsonParseStatement : JSON PARSE identifier INTO identifier (NAME OF? identifier)? onExceptionClause?
                   notOnExceptionClause? END_JSON ;

mergeStatement : MERGE fileName mergeOnKeyClause+ mergeCollatingSequencePhrase? mergeUsing* mergeOutputProcedurePhrase?
               mergeGivingPhrase* ;

mergeOnKeyClause : ON? (ASCENDING | DESCENDING) KEY? qualifiedDataName+ ;

mergeCollatingSequencePhrase : COLLATING? SEQUENCE IS? alphabetName+ mergeCollatingAlphanumeric? mergeCollatingNational? ;

mergeCollatingAlphanumeric : FOR? ALPHANUMERIC IS alphabetName ;

mergeCollatingNational : FOR? NATIONAL IS alphabetName ;

mergeUsing : USING fileName+ ;

mergeOutputProcedurePhrase : OUTPUT PROCEDURE IS? procedureName mergeOutputThrough? ;

mergeOutputThrough : (THROUGH | THRU) procedureName ;

mergeGivingPhrase : GIVING mergeGiving+ ;

mergeGiving : fileName (LOCK | SAVE | NO REWIND | CRUNCH | RELEASE | WITH REMOVE CRUNCH)? ;

moveStatement : MOVE ALL? (moveToStatement | moveCorrespondingToStatement) ;

moveToStatement : moveToSendingArea TO identifier+ ;

moveToSendingArea : identifier | literal ;

moveCorrespondingToStatement : (CORRESPONDING | CORR) moveCorrespondingToSendingArea TO identifier+ ;

moveCorrespondingToSendingArea : identifier ;

multiplyStatement : MULTIPLY (identifier | literal) BY (multiplyRegular | multiplyGiving) onSizeErrorPhrase?
                  notOnSizeErrorPhrase? END_MULTIPLY? ;

multiplyRegular : multiplyRegularOperand+ ;

multiplyRegularOperand : identifier ROUNDED? ;

multiplyGiving : multiplyGivingOperand GIVING multiplyGivingResult+ ;

multiplyGivingOperand : identifier | literal ;

multiplyGivingResult : identifier ROUNDED? ;

nextSentenceStatement : NEXT SENTENCE ;

openStatement : OPEN (openInputStatement | openOutputStatement | openIOStatement | openExtendStatement)+ ;

openInputStatement : INPUT openInput+ ;

openInput : fileName (REVERSED | WITH? NO REWIND)? ;

openOutputStatement : OUTPUT openOutput+ ;

openOutput : fileName (WITH? NO REWIND)? ;

openIOStatement : I_O fileName+ ;

openExtendStatement : EXTEND fileName+ ;

performStatement : PERFORM (performInlineStatement | performProcedureStatement) ;

performInlineStatement : performType? statement* END_PERFORM ;

performProcedureStatement : procedureName ((THROUGH | THRU) procedureName)? performType? ;

performType : performTimes | performUntil | performVarying ;

performTimes : (identifier | integerLiteral) TIMES ;

performUntil : performTestClause? UNTIL condition ;

performVarying : performTestClause performVaryingClause | performVaryingClause performTestClause? ;

performVaryingClause : VARYING performVaryingPhrase performAfter* ;

performVaryingPhrase : (identifier | literal) performFrom performBy performUntil ;

performAfter : AFTER performVaryingPhrase ;

performFrom : FROM (identifier | literal | arithmeticExpression) ;

performBy : BY (identifier | literal | arithmeticExpression) ;

performTestClause : WITH? (BEFORE | AFTER) ;

purgeStatement : PURGE cdName+ ;

raiseStatement : RAISE (EXCEPTION | identifier) (WITH literal)? ;

readStatement : READ fileName NEXT? RECORD? readInto? readWith? readKey? invalidKeyPhrase? notInvalidKeyPhrase?
              atEndPhrase? notAtEndPhrase? END_READ? ;

readInto : INTO identifier ;

readWith : WITH? ((KEPT | NO) LOCK | WAIT) ;

readKey : KEY IS? qualifiedDataName ;

receiveStatement : RECEIVE (receiveFromStatement | receiveIntoStatement) onExceptionClause? notOnExceptionClause? END_RECEIVE? ;

receiveFromStatement : dataName FROM receiveFrom (receiveBefore | receiveWith | receiveThread | receiveSize | receiveStatus)* ;

receiveFrom : THREAD dataName | LAST THREAD | ANY THREAD ;

receiveIntoStatement : cdName (MESSAGE | SEGMENT) INTO? identifier receiveNoData? receiveWithData? ;

receiveNoData : NO DATA statement* ;

receiveWithData : WITH DATA statement* ;

receiveBefore : BEFORE TIME? (numericLiteral | identifier) ;

receiveWith : WITH? NO WAIT ;

receiveThread : THREAD IN? dataName ;

receiveSize : SIZE IN? (numericLiteral | identifier) ;

receiveStatus : STATUS IN? (identifier) ;

releaseStatement : RELEASE recordName (FROM qualifiedDataName)? ;

resumeStatement : RESUME (AT literal | NEXT STATEMENT) ;

returnStatement : RETURN fileName RECORD? returnInto? atEndPhrase notAtEndPhrase? END_RETURN? ;

returnInto : INTO qualifiedDataName ;

rewriteStatement : REWRITE recordName rewriteFrom? invalidKeyPhrase? notInvalidKeyPhrase? END_REWRITE? ;

rewriteFrom : FROM identifier ;

searchStatement : SEARCH ALL? qualifiedDataName searchVarying? atEndPhrase? searchWhen+ END_SEARCH? ;

searchVarying : VARYING qualifiedDataName ;

searchWhen : WHEN condition (NEXT SENTENCE | statement*) ;

sendStatement : SEND (sendStatementSync | sendStatementAsync) onExceptionClause? notOnExceptionClause? ;

sendStatementSync : (identifier | literal) sendFromPhrase? sendWithPhrase? sendReplacingPhrase? sendAdvancingPhrase? ;

sendStatementAsync : TO (TOP | BOTTOM) identifier ;

sendFromPhrase : FROM identifier ;

sendWithPhrase : WITH (EGI | EMI | ESI | identifier) ;

sendReplacingPhrase : REPLACING LINE? ;

sendAdvancingPhrase : (BEFORE | AFTER) ADVANCING? (sendAdvancingPage | sendAdvancingLines | sendAdvancingMnemonic) ;

sendAdvancingPage : PAGE ;

sendAdvancingLines : (identifier | literal) (LINE | LINES)? ;

sendAdvancingMnemonic : mnemonicName ;

setStatement : SET (setToStatement+ | setUpDownByStatement | setConditionStatement) ;

setToStatement : setTo+ TO setToValue+ ;

setUpDownByStatement : setTo+ (UP BY | DOWN BY) setByValue ;

setConditionStatement : conditionName+ TO (TRUE | FALSE) ;

setTo : identifier ;

setToValue : ON | OFF | ENTRY (identifier | literal) | identifier | literal ;

setByValue : identifier | literal ;

sortStatement : SORT fileName sortOnKeyClause+ sortDuplicatesPhrase? sortCollatingSequencePhrase? sortInputProcedurePhrase?
              sortUsing* sortOutputProcedurePhrase? sortGivingPhrase* ;

sortOnKeyClause : ON? (ASCENDING | DESCENDING) KEY? qualifiedDataName+ ;

sortDuplicatesPhrase : WITH? DUPLICATES IN? ORDER? ;

sortCollatingSequencePhrase : COLLATING? SEQUENCE IS? alphabetName+ sortCollatingAlphanumeric? sortCollatingNational? ;

sortCollatingAlphanumeric : FOR? ALPHANUMERIC IS alphabetName ;

sortCollatingNational : FOR? NATIONAL IS alphabetName ;

sortInputProcedurePhrase : INPUT PROCEDURE IS? procedureName sortInputThrough? ;

sortInputThrough : (THROUGH | THRU) procedureName ;

sortUsing : USING fileName+ ;

sortOutputProcedurePhrase : OUTPUT PROCEDURE IS? procedureName sortOutputThrough? ;

sortOutputThrough : (THROUGH | THRU) procedureName ;

sortGivingPhrase : GIVING sortGiving+ ;

sortGiving : fileName (LOCK | SAVE | NO REWIND | CRUNCH | RELEASE | WITH REMOVE CRUNCH)? ;

startStatement : START fileName startKey? invalidKeyPhrase? notInvalidKeyPhrase? END_START? ;

startKey : KEY IS? (EQUAL TO? | EQUALS | GREATER THAN? | MORETHANCHAR | NOT LESS THAN? | NOT LESSTHANCHAR
                   | GREATER THAN? OR EQUAL TO? | GREATER_THAN_OR_EQUAL) qualifiedDataName ;

stopStatement : STOP (RUN | literal | stopStatementGiving) ;

stopStatementGiving : RUN (GIVING | RETURNING) (identifier | integerLiteral) ;

stringStatement : STRING stringSendingPhrase+ stringIntoPhrase stringWithPointerPhrase? onOverflowPhrase?
                notOnOverflowPhrase? END_STRING? ;

stringSendingPhrase : stringSending (COMMA_CHAR? stringSending)* (stringDelimitedByPhrase | stringForPhrase) ;

stringSending : identifier | literal ;

stringDelimitedByPhrase : DELIMITED BY? (SIZE | identifier | literal) ;

stringForPhrase : FOR (identifier | literal) ;

stringIntoPhrase : INTO identifier ;

stringWithPointerPhrase : WITH? POINTER qualifiedDataName ;

subtractStatement : SUBTRACT (subtractFromStatement | subtractFromGivingStatement | subtractCorrespondingStatement)
                  onSizeErrorPhrase? notOnSizeErrorPhrase? END_SUBTRACT? ;

subtractFromStatement : subtractSubtrahend+ FROM subtractMinuend+ ;

subtractFromGivingStatement : subtractSubtrahend+ FROM subtractMinuendGiving GIVING subtractGiving+ ;

subtractCorrespondingStatement : (CORRESPONDING | CORR) qualifiedDataName FROM subtractMinuendCorresponding ;

subtractSubtrahend : identifier | literal ;

subtractMinuend : identifier ROUNDED? ;

subtractMinuendGiving : identifier | literal ;

subtractGiving : identifier ROUNDED? ;

subtractMinuendCorresponding : qualifiedDataName ROUNDED? ;

terminateStatement : TERMINATE reportName ;

unstringStatement : UNSTRING unstringSendingPhrase unstringIntoPhrase unstringWithPointerPhrase? unstringTallyingPhrase?
                  onOverflowPhrase? notOnOverflowPhrase? END_UNSTRING? ;

unstringSendingPhrase : identifier (unstringDelimitedByPhrase unstringOrAllPhrase*)? ;

unstringDelimitedByPhrase : DELIMITED BY? ALL? (identifier | literal) ;

unstringOrAllPhrase : OR ALL? (identifier | literal) ;

unstringIntoPhrase : INTO unstringInto+ ;

unstringInto : identifier unstringDelimiterIn? unstringCountIn? ;

unstringDelimiterIn : DELIMITER IN? identifier ;

unstringCountIn : COUNT IN? identifier ;

unstringWithPointerPhrase : WITH? POINTER qualifiedDataName ;

unstringTallyingPhrase : TALLYING IN? qualifiedDataName ;

useStatement : USE (useAfterClause | useDebugClause | useBeforeReportingClause | useExceptionClause | useGlobalClause) ;

useAfterClause : AFTER STANDARD? (ERROR | EXCEPTION) PROCEDURE? ON (fileName+ | INPUT | OUTPUT | I_O | EXTEND) ;

useDebugClause : FOR? DEBUGGING ON (procedureName | ALL PROCEDURES | fileName | mnemonicName) ;

useBeforeReportingClause : BEFORE REPORTING reportName ;

useExceptionClause : AFTER EXCEPTION CONDITION ;

useGlobalClause : GLOBAL ;

writeStatement : WRITE recordName writeFromPhrase? writeAdvancingPhrase? writeAtEndOfPagePhrase? writeNotAtEndOfPagePhrase?
               invalidKeyPhrase? notInvalidKeyPhrase? END_WRITE? ;

writeFromPhrase : FROM (identifier | literal) ;

writeAdvancingPhrase : (BEFORE | AFTER) ADVANCING? (writeAdvancingPage | writeAdvancingLines | writeAdvancingMnemonic) ;

writeAdvancingPage : PAGE ;

writeAdvancingLines : (identifier | literal) (LINE | LINES)? ;

writeAdvancingMnemonic : mnemonicName ;

writeAtEndOfPagePhrase : AT? (END_OF_PAGE | EOP) statement* ;

writeNotAtEndOfPagePhrase : NOT AT? (END_OF_PAGE | EOP) statement* ;

xmlGenerateStatement : XML GENERATE identifier FROM identifier (COUNT IN? identifier)? (NAMESPACE identifier)?
                     (NAMESPACE_PREFIX identifier)? onExceptionClause? notOnExceptionClause? END_XML ;

xmlParseStatement : XML PARSE identifier PROCESSING PROCEDURE IS? procedureName xmlParseOptions* onExceptionClause?
                  notOnExceptionClause? END_XML ;

xmlParseOptions : VALIDATING WITH? (xmlSchemaName | FILE literal) | RETURNING NATIONAL | ENCODING literal ;

xmlSchemaName : identifier ;

// Object-Oriented COBOL constructs
classDefinition : CLASS_ID DOT className (INHERITS className)? DOT classEnvironmentDivision? factoryDefinition?
                objectDefinition? END CLASS className DOT ;

classEnvironmentDivision : ENVIRONMENT DIVISION DOT environmentDivisionBody* ;

factoryDefinition : FACTORY DOT factoryDataDivision? factoryProcedureDivision? END FACTORY DOT ;

objectDefinition : OBJECT DOT objectDataDivision? objectProcedureDivision? END OBJECT DOT ;

factoryDataDivision : DATA DIVISION DOT dataDivisionSection* ;

objectDataDivision : DATA DIVISION DOT dataDivisionSection* ;


factoryProcedureDivision : PROCEDURE DIVISION DOT procedureDivisionBody methodDefinition* ;

objectProcedureDivision : PROCEDURE DIVISION DOT procedureDivisionBody methodDefinition* ;

methodDefinition : METHOD_ID DOT methodName DOT procedureDivisionUsingClause? procedureDivisionGivingClause?
                 dataDivision? procedureDivisionBody END METHOD methodName DOT ;

interfaceDefinition : INTERFACE_ID DOT interfaceName DOT interfaceProcedureDivision? END INTERFACE interfaceName DOT ;

interfaceProcedureDivision : PROCEDURE DIVISION DOT methodPrototype* ;

methodPrototype : METHOD_ID DOT methodName procedureDivisionUsingClause? procedureDivisionGivingClause? DOT ;

functionDefinition : FUNCTION_ID DOT functionName DOT functionEnvironmentDivision? functionDataDivision?
                  functionProcedureDivision END FUNCTION functionName DOT ;

functionEnvironmentDivision : ENVIRONMENT DIVISION DOT environmentDivisionBody* ;

functionDataDivision : DATA DIVISION DOT linkageSection ;

functionProcedureDivision : PROCEDURE DIVISION procedureDivisionUsingClause procedureDivisionGivingClause DOT
                         procedureDivisionBody ;

// Exception handling phrases
atEndPhrase : AT? END statement* ;

notAtEndPhrase : NOT AT? END statement* ;

invalidKeyPhrase : INVALID KEY? statement* ;

notInvalidKeyPhrase : NOT INVALID KEY? statement* ;

onOverflowPhrase : ON? OVERFLOW statement* ;

notOnOverflowPhrase : NOT ON? OVERFLOW statement* ;

onSizeErrorPhrase : ON? SIZE ERROR statement* ;

notOnSizeErrorPhrase : NOT ON? SIZE ERROR statement* ;

onExceptionClause : ON? EXCEPTION statement* ;

notOnExceptionClause : NOT ON? EXCEPTION statement* ;

// Arithmetic expressions
arithmeticExpression : multDivs plusMinus* ;

plusMinus : (PLUSCHAR | MINUSCHAR) multDivs ;

multDivs : powers multDiv* ;

multDiv : (ASTERISK | SLASH) powers ;

powers : (PLUSCHAR | MINUSCHAR)? basis power* ;

power : DOUBLEASTERISK basis ;

basis : LPARENCHAR arithmeticExpression RPARENCHAR | identifier | literal ;

// Conditions
condition : combinableCondition andOrCondition* ;

andOrCondition : (AND | OR) (combinableCondition | abbreviation+) ;

combinableCondition : NOT? simpleCondition ;

simpleCondition : LPARENCHAR condition RPARENCHAR | relationCondition | classCondition | conditionNameReference ;

classCondition : identifier IS? NOT? (NUMERIC | ALPHABETIC | ALPHABETIC_LOWER | ALPHABETIC_UPPER | DBCS | KANJI | className) ;

conditionNameReference : conditionName (inData* inFile? conditionNameSubscriptReference* | inMnemonic*) ;

conditionNameSubscriptReference : LPARENCHAR subscript (COMMA_CHAR? subscript)* RPARENCHAR ;

relationCondition : relationSignCondition | relationArithmeticComparison | relationCombinedComparison ;

relationSignCondition : arithmeticExpression IS? NOT? (POSITIVE | NEGATIVE | ZERO) ;

relationArithmeticComparison : arithmeticExpression relationalOperator arithmeticExpression ;

relationCombinedComparison : arithmeticExpression relationalOperator LPARENCHAR relationCombinedCondition RPARENCHAR ;

relationCombinedCondition : arithmeticExpression ((AND | OR) arithmeticExpression)+ ;

relationalOperator : (IS | ARE)? (NOT? (GREATER THAN? | MORETHANCHAR | LESS THAN? | LESSTHANCHAR | EQUAL TO? | EQUALS)
                    | NOT_EQUAL | GREATER_THAN_OR_EQUAL | LESS_THAN_OR_EQUAL) ;

abbreviation : NOT? relationalOperator? (arithmeticExpression | LPARENCHAR arithmeticExpression abbreviation RPARENCHAR) ;

// Identifiers and references
identifier : qualifiedDataName | tableCall | functionCall | specialRegister | objectReference | methodReference ;

tableCall : qualifiedDataName (LPARENCHAR subscript (COMMA_CHAR? subscript)* RPARENCHAR)* referenceModifier? ;

functionCall : FUNCTION functionName (LPARENCHAR argument (COMMA_CHAR? argument)* RPARENCHAR)* referenceModifier? ;

objectReference : qualifiedDataName OBJECT_REFERENCE_OP qualifiedDataName ;

methodReference : qualifiedDataName METHOD_REFERENCE_OP methodName ;

referenceModifier : LPARENCHAR characterPosition COLON length? RPARENCHAR ;

characterPosition : arithmeticExpression ;

length : arithmeticExpression ;

subscript : ALL | integerLiteral | qualifiedDataName integerLiteral? | indexName integerLiteral? | arithmeticExpression ;

argument : literal | identifier | qualifiedDataName integerLiteral? | indexName integerLiteral? | arithmeticExpression ;

qualifiedDataName : qualifiedDataNameFormat1 | qualifiedDataNameFormat2 | qualifiedDataNameFormat3 | qualifiedDataNameFormat4 ;

qualifiedDataNameFormat1 : (dataName | conditionName) (qualifiedInData+ inFile? | inFile)? ;

qualifiedDataNameFormat2 : paragraphName inSection ;

qualifiedDataNameFormat3 : textName inLibrary ;

qualifiedDataNameFormat4 : LINAGE_COUNTER inFile ;

qualifiedInData : inData | inTable ;

inData : (IN | OF) dataName ;

inFile : (IN | OF) fileName ;

inMnemonic : (IN | OF) mnemonicName ;

inSection : (IN | OF) sectionName ;

inLibrary : (IN | OF) libraryName ;

inTable : (IN | OF) tableCall ;

// Name definitions
alphabetName : cobolWord ;

assignmentName : systemName ;

basisName : programName ;

cdName : cobolWord ;

className : cobolWord ;

computerName : systemName ;

conditionName : cobolWord ;

dataName : cobolWord ;

dataDescName : FILLER | CURSOR | dataName ;

environmentName : systemName ;

fileName : cobolWord ;

functionName : INTEGER | LENGTH | RANDOM | SUM | WHEN_COMPILED | cobolWord ;

indexName : cobolWord ;

interfaceName : cobolWord ;

languageName : systemName ;

libraryName : cobolWord ;

localName : cobolWord ;

methodName : cobolWord ;

mnemonicName : cobolWord ;

paragraphName : cobolWord | integerLiteral ;

procedureName : paragraphName inSection? | sectionName ;

programName : NONNUMERICLITERAL | cobolWord ;

recordName : qualifiedDataName ;

reportName : qualifiedDataName ;

routineName : cobolWord ;

screenName : cobolWord ;

sectionName : cobolWord | integerLiteral ;

systemName : cobolWord ;

symbolicCharacter : cobolWord ;

textName : cobolWord ;

cobolWord : IDENTIFIER ;

// Literals and constants
literal : NONNUMERICLITERAL | figurativeConstant | numericLiteral | booleanLiteral | cicsDfhRespLiteral | cicsDfhValueLiteral ;

booleanLiteral : TRUE | FALSE ;

numericLiteral : NUMERICLITERAL | ZERO | integerLiteral ;

// Enhanced integer literal to support all level numbers

integerLiteral : NUMERICLITERAL | INTEGERLITERAL | LEVEL_NUMBER_01 | LEVEL_NUMBER_02 | LEVEL_NUMBER_03 
               | LEVEL_NUMBER_04 | LEVEL_NUMBER_05 | LEVEL_NUMBER_66 | LEVEL_NUMBER_77 | LEVEL_NUMBER_88 ;


// Enhanced to support all valid level numbers 01-49
integerLevelNumber : INTEGERLITERAL | LEVEL_NUMBER_01 | LEVEL_NUMBER_02 | LEVEL_NUMBER_03 | LEVEL_NUMBER_04 
                   | LEVEL_NUMBER_05 | LEVEL_NUMBER_77 | LEVEL_NUMBER_66 | LEVEL_NUMBER_88 ;

cicsDfhRespLiteral : DFHRESP LPARENCHAR (cobolWord | literal) RPARENCHAR ;

cicsDfhValueLiteral : DFHVALUE LPARENCHAR (cobolWord | literal) RPARENCHAR ;

figurativeConstant : ALL literal | HIGH_VALUE | HIGH_VALUES | LOW_VALUE | LOW_VALUES | NULL | NULLS
                   | QUOTE | QUOTES | SPACE | SPACES | ZERO | ZEROS | ZEROES ;

specialRegister : ADDRESS OF identifier | DATE | DAY | DAY_OF_WEEK | DEBUG_CONTENTS | DEBUG_ITEM | DEBUG_LINE
                | DEBUG_NAME | DEBUG_SUB_1 | DEBUG_SUB_2 | DEBUG_SUB_3 | LENGTH OF? identifier | LINAGE_COUNTER
                | LINE_COUNTER | PAGE_COUNTER | RETURN_CODE | SHIFT_IN | SHIFT_OUT | SORT_CONTROL | SORT_CORE_SIZE
                | SORT_FILE_SIZE | SORT_MESSAGE | SORT_MODE_SIZE | SORT_RETURN | TALLY | TIME | WHEN_COMPILED ;

// Enhanced operator definition for better parsing
operator : PLUSCHAR | MINUSCHAR | ASTERISK | SLASH | DOUBLEASTERISK | EQUALS | NOT_EQUAL | LESSTHANCHAR 
         | MORETHANCHAR | LESS_THAN_OR_EQUAL | GREATER_THAN_OR_EQUAL | AMPERSAND | DOLLAR ;

// Enhanced error recovery
error : .+? (DOT | DIVISION | SECTION | PARAGRAPH | END | EOF) ;

//=====================================================================================
// LEXER RULES
//=====================================================================================

// Enhanced whitespace handling for COBOL format
//WS : [ \t\r\n]+ -> skip ;

NEWLINE : '\r'? '\n' -> skip ;
WS : [ \t]+ -> skip ;


// Enhanced comment handling  
//COMMENTENTRYLINE : ('*' | '/' | 'C' | 'c' | 'D' | 'd') ~[\r\n]* [\r\n]? -> channel(HIDDEN) ;

//COMMENTENTRYLINE : ( '*' | '/' | '$' ) ~[\r\n]* [\r\n]? -> channel(HIDDEN) ;
// Line continuation handling
//CONTINUATION_LINE : [0-9] [0-9] [0-9] [0-9] [0-9] [0-9] '-' ~[\r\n]* [\r\n]? -> channel(HIDDEN) ;

COMMENTENTRYLINE : ( '*' | '/' | '$' ) ~[\r\n]* -> channel(HIDDEN) ;
CONTINUATION_LINE : [0-9] [0-9] [0-9] [0-9] [0-9] [0-9] '-' ~[\r\n]* -> channel(HIDDEN) ;



// Punctuation and operators
DOT : '.' ;
COMMA_CHAR : ',' ;
SEMICOLON : ';' ;
COLON : ':' ;
LPARENCHAR : '(' ;
RPARENCHAR : ')' ;
LBRACKET : '[' ;
RBRACKET : ']' ;
PLUSCHAR : '+' ;
MINUSCHAR : '-' ;
ASTERISK : '*' ;
DOUBLEASTERISK : '**' ;
SLASH : '/' ;
EQUALS : '=' ;
NOT_EQUAL : '<>' | '!=' | '≠' ;
LESSTHANCHAR : '<' ;
MORETHANCHAR : '>' ;
LESS_THAN_OR_EQUAL : '<=' | '≤' ;
GREATER_THAN_OR_EQUAL : '>=' | '≥' ;
AMPERSAND : '&' ;
DOLLAR : '$' ;

// Object-oriented operators
OBJECT_REFERENCE_OP : '::' ;
METHOD_REFERENCE_OP : '->' ;

// Enhanced level numbers (common level numbers only)
LEVEL_NUMBER_01 : '01' ;
LEVEL_NUMBER_02 : '02' ;
LEVEL_NUMBER_03 : '03' ;
LEVEL_NUMBER_04 : '04' ;
LEVEL_NUMBER_05 : '05' ;
LEVEL_NUMBER_66 : '66' ;
LEVEL_NUMBER_77 : '77' ;
LEVEL_NUMBER_88 : '88' ;

// Enhanced literal handling
NONNUMERICLITERAL : ('"' (~["\r\n] | '""')* '"' | '\'' (~['\r\n] | '\'\'')* '\'' | 'X"' [0-9A-Fa-f]* '"' | 'H"' [0-9A-Fa-f]* '"') ;
NUMERICLITERAL : [0-9]+ ('.' [0-9]+)? ([eE] [+-]? [0-9]+)? ;
INTEGERLITERAL : [0-9]+ ;

// Pseudo text delimiter
PSEUDO_TEXT_DELIMITER : '==' ;

//SEQUENCE_AREA : [ \t]{10,} [A-Za-z0-9.-]+ [ \t]* -> channel(HIDDEN) ;
//safest rules

SEQUENCE_AREA : {getCharPositionInLine() > 50}? [A-Za-z0-9.-]+ -> channel(HIDDEN) ;


// COBOL Keywords (alphabetically ordered)
ABORT : 'ABORT' ;
ACCEPT : 'ACCEPT' ;
ACCESS : 'ACCESS' ;
ADD : 'ADD' ;
ADDRESS : 'ADDRESS' ;
ADVANCING : 'ADVANCING' ;
AFTER : 'AFTER' ;
ALIGNED : 'ALIGNED' ;
ALL : 'ALL' ;
ALLOCATE : 'ALLOCATE' ;
ALPHABET : 'ALPHABET' ;
ALPHABETIC : 'ALPHABETIC' ;
ALPHABETIC_LOWER : 'ALPHABETIC-LOWER' ;
ALPHABETIC_UPPER : 'ALPHABETIC-UPPER' ;
ALPHANUMERIC : 'ALPHANUMERIC' ;
ALPHANUMERIC_EDITED : 'ALPHANUMERIC-EDITED' ;
ALSO : 'ALSO' ;
ALTER : 'ALTER' ;
ALTERNATE : 'ALTERNATE' ;
AND : 'AND' ;
ANY : 'ANY' ;
ARE : 'ARE' ;
AREA : 'AREA' ;
AREAS : 'AREAS' ;
AS : 'AS' ;
ASCENDING : 'ASCENDING' ;
ASCII : 'ASCII' ;
ASSIGN : 'ASSIGN' ;
ASSOCIATED_DATA : 'ASSOCIATED-DATA' ;
ASSOCIATED_DATA_LENGTH : 'ASSOCIATED-DATA-LENGTH' ;
AT : 'AT' ;
ATTRIBUTE : 'ATTRIBUTE' ;
AUTHOR : 'AUTHOR' ;
AUTO : 'AUTO' ;
AUTO_SKIP : 'AUTO-SKIP' ;
AUTOMATIC : 'AUTOMATIC' ;
BACKGROUND_COLOR : 'BACKGROUND-COLOR' ;
BACKGROUND_COLOUR : 'BACKGROUND-COLOUR' ;
BASED : 'BASED' ;
BEEP : 'BEEP' ;
BEFORE : 'BEFORE' ;
BELL : 'BELL' ;
BINARY : 'BINARY' ;
BIT : 'BIT' ;
BLANK : 'BLANK' ;
BLINK : 'BLINK' ;
BLOB : 'BLOB' ;
BLOCK : 'BLOCK' ;
BOTTOM : 'BOTTOM' ;
BOUNDS : 'BOUNDS' ;
BY : 'BY' ;
BYFUNCTION : 'BYFUNCTION' ;
BYTES : 'BYTES' ;
BYTITLE : 'BYTITLE' ;
CALL : 'CALL' ;
CANCEL : 'CANCEL' ;
CAPABLE : 'CAPABLE' ;
CCSVERSION : 'CCSVERSION' ;
CD : 'CD' ;
CF : 'CF' ;
CH : 'CH' ;
CHAINING : 'CHAINING' ;
CHANGED : 'CHANGED' ;
CHANNEL : 'CHANNEL' ;
CHARACTER : 'CHARACTER' ;
CHARACTERS : 'CHARACTERS' ;
CICS : 'CICS' ;
CLASS : 'CLASS' ;
CLASS_ID : 'CLASS-ID' ;
CLOB : 'CLOB' ;
CLOCK_UNITS : 'CLOCK-UNITS' ;
CLOSE : 'CLOSE' ;
CLOSE_DISPOSITION : 'CLOSE-DISPOSITION' ;
COBOL : 'COBOL' ;
CODE_SET : 'CODE-SET' ;
COL : 'COL' ;
COLLATING : 'COLLATING' ;
COLUMN : 'COLUMN' ;
COMMA : 'COMMA' ;
COMMITMENT : 'COMMITMENT' ;
COMMON : 'COMMON' ;
COMMUNICATION : 'COMMUNICATION' ;
COMP : 'COMP' ;
COMP_1 : 'COMP-1' ;
COMP_2 : 'COMP-2' ;
COMP_3 : 'COMP-3' ;
COMP_4 : 'COMP-4' ;
COMP_5 : 'COMP-5' ;
COMP_6 : 'COMP-6' ;
COMPUTATIONAL : 'COMPUTATIONAL' ;
COMPUTATIONAL_1 : 'COMPUTATIONAL-1' ;
COMPUTATIONAL_2 : 'COMPUTATIONAL-2' ;
COMPUTATIONAL_3 : 'COMPUTATIONAL-3' ;
COMPUTATIONAL_4 : 'COMPUTATIONAL-4' ;
COMPUTATIONAL_5 : 'COMPUTATIONAL-5' ;
COMPUTATIONAL_6 : 'COMPUTATIONAL-6' ;
COMPUTE : 'COMPUTE' ;
CONFIGURATION : 'CONFIGURATION' ;
CONTAINS : 'CONTAINS' ;
CONTENT : 'CONTENT' ;
CONTINUE : 'CONTINUE' ;
CONTROL : 'CONTROL' ;
CONTROL_POINT : 'CONTROL-POINT' ;
CONVENTION : 'CONVENTION' ;
CONVERTING : 'CONVERTING' ;
COPY : 'COPY' ;
CORR : 'CORR' ;
CORRESPONDING : 'CORRESPONDING' ;
COUNT : 'COUNT' ;
CRUNCH : 'CRUNCH' ;
CURRENCY : 'CURRENCY' ;
CURSOR : 'CURSOR' ;
DATA : 'DATA' ;
DATA_BASE : 'DATA-BASE' ;
DATE : 'DATE' ;
DATE_COMPILED : 'DATE-COMPILED' ;
DATE_WRITTEN : 'DATE-WRITTEN' ;
DAY : 'DAY' ;
DAY_OF_WEEK : 'DAY-OF-WEEK' ;
DBCS : 'DBCS' ;
DBCLOB : 'DBCLOB' ;
DE : 'DE' ;
DEBUG_CONTENTS : 'DEBUG-CONTENTS' ;
DEBUG_ITEM : 'DEBUG-ITEM' ;
DEBUG_LINE : 'DEBUG-LINE' ;
DEBUG_NAME : 'DEBUG-NAME' ;
DEBUG_SUB_1 : 'DEBUG-SUB-1' ;
DEBUG_SUB_2 : 'DEBUG-SUB-2' ;
DEBUG_SUB_3 : 'DEBUG-SUB-3' ;
DEBUGGING : 'DEBUGGING' ;
DECIMAL_POINT : 'DECIMAL-POINT' ;
DECLARATIVES : 'DECLARATIVES' ;
DEFAULT : 'DEFAULT' ;
DEFAULT_DISPLAY : 'DEFAULT-DISPLAY' ;
DEFINITION : 'DEFINITION' ;
DELETE : 'DELETE' ;
DELIMITED : 'DELIMITED' ;
DELIMITER : 'DELIMITER' ;
DEPENDING : 'DEPENDING' ;
DESCENDING : 'DESCENDING' ;
DESTINATION : 'DESTINATION' ;
DETAIL : 'DETAIL' ;
DFHRESP : 'DFHRESP' ;
DFHVALUE : 'DFHVALUE' ;
DISABLE : 'DISABLE' ;
DISK : 'DISK' ;
DISPLAY : 'DISPLAY' ;
DISPLAY_1 : 'DISPLAY-1' ;
DIVIDE : 'DIVIDE' ;
DIVISION : 'DIVISION' ;
DONTCARE : 'DONTCARE' ;
DOUBLE : 'DOUBLE' ;
DOWN : 'DOWN' ;
DUPLICATES : 'DUPLICATES' ;
DYNAMIC : 'DYNAMIC' ;
EBCDIC : 'EBCDIC' ;
EGCS : 'EGCS' ;
EGI : 'EGI' ;
ELSE : 'ELSE' ;
EMI : 'EMI' ;
EMPTY_CHECK : 'EMPTY-CHECK' ;
ENABLE : 'ENABLE' ;
ENCODING : 'ENCODING' ;
END : 'END' ;
END_ACCEPT : 'END-ACCEPT' ;
END_ADD : 'END-ADD' ;
END_ALLOCATE : 'END-ALLOCATE' ;
END_CALL : 'END-CALL' ;
END_COMPUTE : 'END-COMPUTE' ;
END_DELETE : 'END-DELETE' ;
END_DISPLAY : 'END-DISPLAY' ;
END_DIVIDE : 'END-DIVIDE' ;
END_EVALUATE : 'END-EVALUATE' ;
END_EXEC : 'END-EXEC' ;
END_FREE : 'END-FREE' ;
END_IF : 'END-IF' ;
END_INVOKE : 'END-INVOKE' ;
END_JSON : 'END-JSON' ;
END_MULTIPLY : 'END-MULTIPLY' ;
END_OF_PAGE : 'END-OF-PAGE' ;
END_PERFORM : 'END-PERFORM' ;
END_READ : 'END-READ' ;
END_RECEIVE : 'END-RECEIVE' ;
END_RETURN : 'END-RETURN' ;
END_REWRITE : 'END-REWRITE' ;
END_SEARCH : 'END-SEARCH' ;
END_START : 'END-START' ;
END_STRING : 'END-STRING' ;
END_SUBTRACT : 'END-SUBTRACT' ;
END_UNSTRING : 'END-UNSTRING' ;
END_WRITE : 'END-WRITE' ;
END_XML : 'END-XML' ;
ENTER : 'ENTER' ;
ENTRY : 'ENTRY' ;
ENTRY_PROCEDURE : 'ENTRY-PROCEDURE' ;
ENVIRONMENT : 'ENVIRONMENT' ;
EOL : 'EOL' ;
EOP : 'EOP' ;
EOS : 'EOS' ;
EQUAL : 'EQUAL' ;
ERROR : 'ERROR' ;
ESCAPE : 'ESCAPE' ;
ESI : 'ESI' ;
EVALUATE : 'EVALUATE' ;
EVENT : 'EVENT' ;
EVERY : 'EVERY' ;
EXCEPTION : 'EXCEPTION' ;
EXCLUSIVE : 'EXCLUSIVE' ;
EXEC : 'EXEC' ;
EXHIBIT : 'EXHIBIT' ;
EXIT : 'EXIT' ;
EXPORT : 'EXPORT' ;
EXTEND : 'EXTEND' ;
EXTENDED : 'EXTENDED' ;
EXTERNAL : 'EXTERNAL' ;
FACTORY : 'FACTORY' ;
FALSE : 'FALSE' ;
FD : 'FD' ;
FILE : 'FILE' ;
FILE_CONTROL : 'FILE-CONTROL' ;
FILLER : 'FILLER' ;
FINAL : 'FINAL' ;
FIRST : 'FIRST' ;
FLOAT_BINARY_32 : 'FLOAT-BINARY-32' ;
FLOAT_BINARY_64 : 'FLOAT-BINARY-64' ;
FLOAT_DECIMAL_16 : 'FLOAT-DECIMAL-16' ;
FLOAT_DECIMAL_34 : 'FLOAT-DECIMAL-34' ;
FLOAT_EXTENDED : 'FLOAT-EXTENDED' ;
FOOTING : 'FOOTING' ;
FOR : 'FOR' ;
FOREGROUND_COLOR : 'FOREGROUND-COLOR' ;
FOREGROUND_COLOUR : 'FOREGROUND-COLOUR' ;
FREE : 'FREE' ;
FROM : 'FROM' ;
FULL : 'FULL' ;
FUNCTION : 'FUNCTION' ;
FUNCTION_ID : 'FUNCTION-ID' ;
FUNCTIONNAME : 'FUNCTIONNAME' ;
FUNCTION_POINTER : 'FUNCTION-POINTER' ;
GENERATE : 'GENERATE' ;
GIVING : 'GIVING' ;
GLOBAL : 'GLOBAL' ;
GO : 'GO' ;
GOBACK : 'GOBACK' ;
GREATER : 'GREATER' ;
GRID : 'GRID' ;
GROUP : 'GROUP' ;
HEADING : 'HEADING' ;
HIGH_VALUE : 'HIGH-VALUE' ;
HIGH_VALUES : 'HIGH-VALUES' ;
HIGHLIGHT : 'HIGHLIGHT' ;
I_O : 'I-O' ;
I_O_CONTROL : 'I-O-CONTROL' ;
ID : 'ID' ;
IDENTIFICATION : 'IDENTIFICATION' ;
IF : 'IF' ;
IMS : 'IMS' ;
IMPLICIT : 'IMPLICIT' ;
IMPORT : 'IMPORT' ;
IN : 'IN' ;
INDEX : 'INDEX' ;
INDEXED : 'INDEXED' ;
INDICATE : 'INDICATE' ;
INHERITS : 'INHERITS' ;
INITIAL : 'INITIAL' ;
INITIALIZE : 'INITIALIZE' ;
INITIATE : 'INITIATE' ;
INPUT : 'INPUT' ;
INPUT_OUTPUT : 'INPUT-OUTPUT' ;
INSPECT : 'INSPECT' ;
INSTALLATION : 'INSTALLATION' ;
INTEGER : 'INTEGER' ;
INTERFACE : 'INTERFACE' ;
INTERFACE_ID : 'INTERFACE-ID' ;
INTO : 'INTO' ;
INTRINSIC : 'INTRINSIC' ;
INVALID : 'INVALID' ;
INVOKE : 'INVOKE' ;
IS : 'IS' ;
JSON : 'JSON' ;
JUST : 'JUST' ;
JUSTIFIED : 'JUSTIFIED' ;
KANJI : 'KANJI' ;
KEPT : 'KEPT' ;
KEY : 'KEY' ;
KEYBOARD : 'KEYBOARD' ;
LABEL : 'LABEL' ;
LANGUAGE : 'LANGUAGE' ;
LAST : 'LAST' ;
LB : 'LB' ;
LD : 'LD' ;
LEADING : 'LEADING' ;
LEFT : 'LEFT' ;
LEFTLINE : 'LEFTLINE' ;
LENGTH : 'LENGTH' ;
LENGTH_CHECK : 'LENGTH-CHECK' ;
LESS : 'LESS' ;
LIBACCESS : 'LIBACCESS' ;
LIBPARAMETER : 'LIBPARAMETER' ;
LIBRARY : 'LIBRARY' ;
LIMIT : 'LIMIT' ;
LIMITS : 'LIMITS' ;
LINAGE : 'LINAGE' ;
LINAGE_COUNTER : 'LINAGE-COUNTER' ;
LINE : 'LINE' ;
LINE_COUNTER : 'LINE-COUNTER' ;
LINES : 'LINES' ;
LINKAGE : 'LINKAGE' ;
LIST : 'LIST' ;
LOCAL : 'LOCAL' ;
LOCAL_STORAGE : 'LOCAL-STORAGE' ;
LOCK : 'LOCK' ;
LONG_DATE : 'LONG-DATE' ;
LONG_TIME : 'LONG-TIME' ;
LOW_VALUE : 'LOW-VALUE' ;
LOW_VALUES : 'LOW-VALUES' ;
LOWER : 'LOWER' ;
LOWLIGHT : 'LOWLIGHT' ;
MANUAL : 'MANUAL' ;
MEMORY : 'MEMORY' ;
MERGE : 'MERGE' ;
MESSAGE : 'MESSAGE' ;
METHOD : 'METHOD' ;
METHOD_ID : 'METHOD-ID' ;
MMDDYYYY : 'MMDDYYYY' ;
MODE : 'MODE' ;
MODULES : 'MODULES' ;
MOVE : 'MOVE' ;
MULTIPLE : 'MULTIPLE' ;
MULTIPLY : 'MULTIPLY' ;
NAME : 'NAME' ;
NAMED : 'NAMED' ;
NAMESPACE : 'NAMESPACE' ;
NAMESPACE_PREFIX : 'NAMESPACE-PREFIX' ;
NATIONAL : 'NATIONAL' ;
NATIONAL_EDITED : 'NATIONAL-EDITED' ;
NATIVE : 'NATIVE' ;
NEGATIVE : 'NEGATIVE' ;
NETWORK : 'NETWORK' ;
NEXT : 'NEXT' ;
NO : 'NO' ;
NO_ECHO : 'NO-ECHO' ;
NOT : 'NOT' ;
NULL : 'NULL' ;
NULLS : 'NULLS' ;
NUMBER : 'NUMBER' ;
NUMERIC : 'NUMERIC' ;
NUMERIC_DATE : 'NUMERIC-DATE' ;
NUMERIC_EDITED : 'NUMERIC-EDITED' ;
NUMERIC_TIME : 'NUMERIC-TIME' ;
OBJECT : 'OBJECT' ;
OBJECT_COMPUTER : 'OBJECT-COMPUTER' ;
OBJECT_REFERENCE : 'OBJECT-REFERENCE' ;
OCCURS : 'OCCURS' ;
ODT : 'ODT' ;
OF : 'OF' ;
OFF : 'OFF' ;
OMITTED : 'OMITTED' ;
ON : 'ON' ;
ONLY : 'ONLY' ;
OPEN : 'OPEN' ;
OPTIONAL : 'OPTIONAL' ;
OR : 'OR' ;
ORDER : 'ORDER' ;
ORDERLY : 'ORDERLY' ;
ORGANIZATION : 'ORGANIZATION' ;
OTHER : 'OTHER' ;
OUTPUT : 'OUTPUT' ;
OVERFLOW : 'OVERFLOW' ;
OVERLINE : 'OVERLINE' ;
OWN : 'OWN' ;
PACKED_DECIMAL : 'PACKED-DECIMAL' ;
PADDING : 'PADDING' ;
PAGE : 'PAGE' ;
PAGE_COUNTER : 'PAGE-COUNTER' ;
PARAGRAPH : 'PARAGRAPH' ;
PARSE : 'PARSE' ;
PASSWORD : 'PASSWORD' ;
PERFORM : 'PERFORM' ;
PF : 'PF' ;
PH : 'PH' ;
PIC : 'PIC' ;
PICTURE : 'PICTURE' ;
PLUS : 'PLUS' ;
POINTER : 'POINTER' ;
PORT : 'PORT' ;
POSITION : 'POSITION' ;
POSITIVE : 'POSITIVE' ;
PRINTER : 'PRINTER' ;
PRIVATE : 'PRIVATE' ;
PROCEDURE : 'PROCEDURE' ;
PROCEDURE_POINTER : 'PROCEDURE-POINTER' ;
PROCEDURES : 'PROCEDURES' ;
PROCEED : 'PROCEED' ;
PROCESSING : 'PROCESSING' ;
PROGRAM : 'PROGRAM' ;
PROGRAM_ID : 'PROGRAM-ID' ;
PROGRAM_LIBRARY : 'PROGRAM-LIBRARY' ;
PROMPT : 'PROMPT' ;
PURGE : 'PURGE' ;
QUEUE : 'QUEUE' ;
QUOTE : 'QUOTE' ;
QUOTES : 'QUOTES' ;
RAISE : 'RAISE' ;
RAISING : 'RAISING' ;
RANDOM : 'RANDOM' ;
RD : 'RD' ;
READ : 'READ' ;
READER : 'READER' ;
REAL : 'REAL' ;
RECEIVE : 'RECEIVE' ;
RECEIVED : 'RECEIVED' ;
RECORD : 'RECORD' ;
RECORD_AREA : 'RECORD-AREA' ;
RECORDING : 'RECORDING' ;
RECORDS : 'RECORDS' ;
RECURSIVE : 'RECURSIVE' ;
REDEFINES : 'REDEFINES' ;
REEL : 'REEL' ;
REF : 'REF' ;
REFERENCE : 'REFERENCE' ;
REFERENCES : 'REFERENCES' ;
RELATIVE : 'RELATIVE' ;
RELEASE : 'RELEASE' ;
REMAINDER : 'REMAINDER' ;
REMARKS : 'REMARKS' ;
REMOTE : 'REMOTE' ;
REMOVAL : 'REMOVAL' ;
REMOVE : 'REMOVE' ;
RENAMES : 'RENAMES' ;
REPLACING : 'REPLACING' ;
REPORT : 'REPORT' ;
REPORTING : 'REPORTING' ;
REPORTS : 'REPORTS' ;
REPOSITORY : 'REPOSITORY' ;
REQUIRED : 'REQUIRED' ;
RERUN : 'RERUN' ;
RESERVE : 'RESERVE' ;
RESET : 'RESET' ;
RESUME : 'RESUME' ;
RETURN : 'RETURN' ;
RETURN_CODE : 'RETURN-CODE' ;
RETURNING : 'RETURNING' ;
REVERSE_VIDEO : 'REVERSE-VIDEO' ;
REVERSED : 'REVERSED' ;
REWIND : 'REWIND' ;
REWRITE : 'REWRITE' ;
RF : 'RF' ;
RH : 'RH' ;
RIGHT : 'RIGHT' ;
ROUNDED : 'ROUNDED' ;
RUN : 'RUN' ;
SAME : 'SAME' ;
SAVE : 'SAVE' ;
SCREEN : 'SCREEN' ;
SD : 'SD' ;
SEARCH : 'SEARCH' ;
SECTION : 'SECTION' ;
SECURE : 'SECURE' ;
SECURITY : 'SECURITY' ;
SEGMENT : 'SEGMENT' ;
SEGMENT_LIMIT : 'SEGMENT-LIMIT' ;
SELECT : 'SELECT' ;
SELF : 'SELF' ;
SEND : 'SEND' ;
SENTENCE : 'SENTENCE' ;
SEPARATE : 'SEPARATE' ;
SEQUENCE : 'SEQUENCE' ;
SEQUENTIAL : 'SEQUENTIAL' ;
SET : 'SET' ;
SHAREDBYALL : 'SHAREDBYALL' ;
SHAREDBYRUNUNIT : 'SHAREDBYRUNUNIT' ;
SHARING : 'SHARING' ;
SHIFT_IN : 'SHIFT-IN' ;
SHIFT_OUT : 'SHIFT-OUT' ;
SHORT_DATE : 'SHORT-DATE' ;
SIGN : 'SIGN' ;
SIZE : 'SIZE' ;
SORT : 'SORT' ;
SORT_CONTROL : 'SORT-CONTROL' ;
SORT_CORE_SIZE : 'SORT-CORE-SIZE' ;
SORT_FILE_SIZE : 'SORT-FILE-SIZE' ;
SORT_MERGE : 'SORT-MERGE' ;
SORT_MESSAGE : 'SORT-MESSAGE' ;
SORT_MODE_SIZE : 'SORT-MODE-SIZE' ;
SORT_RETURN : 'SORT-RETURN' ;
SOURCE : 'SOURCE' ;
SOURCE_COMPUTER : 'SOURCE-COMPUTER' ;
SPACE : 'SPACE' ;
SPACES : 'SPACES' ;
SPECIAL_NAMES : 'SPECIAL-NAMES' ;
SQL : 'SQL' ;
STANDARD : 'STANDARD' ;
STANDARD_1 : 'STANDARD-1' ;
STANDARD_2 : 'STANDARD-2' ;
START : 'START' ;
STATEMENT : 'STATEMENT' ;
STATUS : 'STATUS' ;
STOP : 'STOP' ;
STRING : 'STRING' ;
SUB_QUEUE_1 : 'SUB-QUEUE-1' ;
SUB_QUEUE_2 : 'SUB-QUEUE-2' ;
SUB_QUEUE_3 : 'SUB-QUEUE-3' ;
SUBTRACT : 'SUBTRACT' ;
SUM : 'SUM' ;
SUPER : 'SUPER' ;
SUPPRESS : 'SUPPRESS' ;
SYMBOL : 'SYMBOL' ;
SYMBOLIC : 'SYMBOLIC' ;
SYNC : 'SYNC' ;
SYNCHRONIZED : 'SYNCHRONIZED' ;
TABLE : 'TABLE' ;
TALLY : 'TALLY' ;
TALLYING : 'TALLYING' ;
TAPE : 'TAPE' ;
TASK : 'TASK' ;
TERMINAL : 'TERMINAL' ;
TERMINATE : 'TERMINATE' ;
TEXT : 'TEXT' ;
THAN : 'THAN' ;
THEN : 'THEN' ;
THREAD : 'THREAD' ;
THREAD_LOCAL : 'THREAD-LOCAL' ;
THROUGH : 'THROUGH' ;
THRU : 'THRU' ;
TIME : 'TIME' ;
TIMER : 'TIMER' ;
TIMES : 'TIMES' ;
TIMESTAMP : 'TIMESTAMP' ;
TIMESTAMP_WITH_TIMEZONE : 'TIMESTAMP-WITH-TIMEZONE' ;
TITLE : 'TITLE' ;
TO : 'TO' ;
TODAYS_DATE : 'TODAYS-DATE' ;
TODAYS_NAME : 'TODAYS-NAME' ;
TOP : 'TOP' ;
TRAILING : 'TRAILING' ;
TRUE : 'TRUE' ;
TRUNCATED : 'TRUNCATED' ;
TYPE : 'TYPE' ;
TYPEDEF : 'TYPEDEF' ;
UNDERLINE : 'UNDERLINE' ;
UNIT : 'UNIT' ;
UNSTRING : 'UNSTRING' ;
UNTIL : 'UNTIL' ;
UP : 'UP' ;
UPON : 'UPON' ;
USAGE : 'USAGE' ;
USE : 'USE' ;
USING : 'USING' ;
UTF_16 : 'UTF-16' ;
UTF_8 : 'UTF-8' ;
VALIDATING : 'VALIDATING' ;
VALUE : 'VALUE' ;
VALUES : 'VALUES' ;
VARYING : 'VARYING' ;
VIRTUAL : 'VIRTUAL' ;
VOLATILE : 'VOLATILE' ;
WAIT : 'WAIT' ;
WHEN : 'WHEN' ;
WHEN_COMPILED : 'WHEN-COMPILED' ;
WITH : 'WITH' ;
WORDS : 'WORDS' ;
WORKING_STORAGE : 'WORKING-STORAGE' ;
WRITE : 'WRITE' ;
XML : 'XML' ;
YEAR : 'YEAR' ;
YYYYDDD : 'YYYYDDD' ;
YYYYMMDD : 'YYYYMMDD' ;
ZERO : 'ZERO' ;
ZERO_FILL : 'ZERO-FILL' ;
ZEROS : 'ZEROS' ;
ZEROES : 'ZEROES' ;

// Additional tokens for better error handling and parsing
CONDITION : 'CONDITION' ;
ERASE : 'ERASE' ;

// Fallback rule for unrecognized tokens (helps with error recovery)
UNKNOWN : . ;

// Enhanced identifier to handle COBOL naming conventions
IDENTIFIER : [A-Za-z] [A-Za-z0-9]* ('-' [A-Za-z0-9]+)* ;

