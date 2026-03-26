CREATE TABLE "texts" ( "url" TEXT NOT NULL UNIQUE, "text" TEXT, "date" TEXT, CONSTRAINT "url" FOREIGN KEY("url") REFERENCES "urls"("url") );
CREATE TABLE "urls" ( "url" TEXT NOT NULL UNIQUE, "title" TEXT, "source" TEXT, "date_created" TEXT, "date_modified" TEXT, "status" INTEGER DEFAULT 0, CONSTRAINT "PK_url" PRIMARY KEY("url") );
CREATE UNIQUE INDEX "IFK_texts_url" ON "urls" ( "url" );