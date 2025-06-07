* Comment line
           PROCESS CICS
           COPY SAMPLE-COPYBOOK.
           REPLACE ==VAR1== BY ==VAR2==.
           MOVE VAR1AR TO WS-VAR.
           REPLACE OFF.
       EXEC CICS LINK PROGRAM('PROG') END-EXEC.
       *>>CE Multi-line comment start
       * Comment continued
           MOVE WS-VAR TO OUTPUT.
           CBL MDECK:
